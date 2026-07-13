import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import get_db
from app.routers import auth, papers, chat, chatbot, upload, rag

# Setup logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def fill_missing_authors(SessionLocal):
    """Background task to populate missing author information for existing papers."""
    import asyncio
    # Wait a few seconds to let uvicorn finish starting up
    await asyncio.sleep(5)
    logger.info("Starting background task to populate missing authors for completed papers...")
    try:
        from sqlalchemy import select
        from app.models.models import Paper, DocumentChunk
        from app.services.llm_service import get_llm_model
        from langchain_core.messages import SystemMessage, HumanMessage

        async with SessionLocal() as db:
            stmt = select(Paper).where(Paper.status == "completed").where((Paper.authors == None) | (Paper.authors == ""))
            res = await db.execute(stmt)
            papers = res.scalars().all()
            
            if not papers:
                logger.info("No papers found with missing authors metadata.")
                return
                
            logger.info(f"Found {len(papers)} completed papers with missing authors. Fetching page 1 content...")
            llm = get_llm_model()
            
            for paper in papers:
                try:
                    # Retrieve the first page chunk of the paper to extract authors
                    stmt_chunk = (
                        select(DocumentChunk)
                        .where(DocumentChunk.paper_id == paper.id)
                        .where(DocumentChunk.page_number == 1)
                        .order_by(DocumentChunk.chunk_index)
                        .limit(1)
                    )
                    res_chunk = await db.execute(stmt_chunk)
                    first_chunk = res_chunk.scalars().first()
                    if not first_chunk:
                        # Fallback to any chunk
                        stmt_chunk_fb = (
                            select(DocumentChunk)
                            .where(DocumentChunk.paper_id == paper.id)
                            .order_by(DocumentChunk.chunk_index)
                            .limit(1)
                        )
                        res_chunk_fb = await db.execute(stmt_chunk_fb)
                        first_chunk = res_chunk_fb.scalars().first()
                        
                    if not first_chunk:
                        logger.warning(f"No text chunks found for paper {paper.id} ({paper.title}). Skipping.")
                        continue
                        
                    logger.info(f"Extracting authors for paper: {paper.title}...")
                    prompt = (
                        "Analyze the following text from the first page of a research paper and extract the author names. "
                        "Return ONLY a comma-separated list of author names (e.g. 'John Doe, Jane Smith'). "
                        "If no authors are found, return 'Unknown'. Do not include any other text.\n\n"
                        f"Text:\n{first_chunk.content}"
                    )
                    messages = [
                        SystemMessage(content="You are a helpful research assistant that extracts metadata."),
                        HumanMessage(content=prompt)
                    ]
                    response = await asyncio.to_thread(llm.invoke, messages)
                    authors = response.content.strip()
                    if authors:
                        paper.authors = authors
                        db.add(paper)
                        await db.commit()
                        logger.info(f"Successfully populated authors for '{paper.title}': {authors}")
                except Exception as paper_ex:
                    logger.error(f"Failed to populate authors for paper {paper.id} ({paper.title}): {paper_ex}")
    except Exception as ex:
        logger.error(f"Failed to complete populate missing authors background task: {ex}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    logger.info("Initializing database tables...")
    try:
        from app.database import engine, Base, SessionLocal
        from sqlalchemy import select, text
        from app.models.models import DocumentChunk, Paper
        async with engine.begin() as conn:
            if "postgresql" in str(engine.url):
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            
            # Run migrations/alter table to add authors column if it does not exist
            try:
                if "postgresql" in str(engine.url):
                    await conn.execute(text("ALTER TABLE papers ADD COLUMN IF NOT EXISTS authors TEXT;"))
                else:
                    # SQLite: check if authors column exists first
                    res = await conn.execute(text("PRAGMA table_info(papers);"))
                    cols = [row[1] for row in res.fetchall()]
                    if "authors" not in cols:
                        await conn.execute(text("ALTER TABLE papers ADD COLUMN authors TEXT;"))
            except Exception as migrate_ex:
                logger.warning(f"Database migration (adding authors column) failed/already done: {migrate_ex}")
                
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialization completed successfully.")
        
        # Trigger background task to populate missing authors for completed papers
        import asyncio
        asyncio.create_task(fill_missing_authors(SessionLocal))
        
        # Sync SQLite chunks to Qdrant if out of sync
        async with SessionLocal() as db:
            stmt_count = select(DocumentChunk)
            res = await db.execute(stmt_count)
            db_chunks = res.scalars().all()
            if db_chunks:
                from app.services.qdrant_service import QdrantService
                client = QdrantService.get_client()
                collection_name = "research_papers"
                
                # Check if collection exists and count points
                needs_sync = False
                try:
                    if not client.collection_exists(collection_name):
                        needs_sync = True
                    else:
                        count_info = client.count(collection_name=collection_name)
                        if count_info.count < len(db_chunks):
                            needs_sync = True
                except Exception as ex:
                    logger.warning(f"Error checking Qdrant collection status: {ex}")
                    needs_sync = True
                
                if needs_sync:
                    logger.info(f"Syncing {len(db_chunks)} chunks from database to Qdrant...")
                    # Fetch paper owner ids
                    stmt_papers = select(Paper)
                    res_papers = await db.execute(stmt_papers)
                    papers_map = {p.id: p.user_id for p in res_papers.scalars().all()}
                    
                    qdrant_chunks = []
                    for chunk in db_chunks:
                        user_id = papers_map.get(chunk.paper_id)
                        qdrant_chunks.append({
                            "id": chunk.id,
                            "content": chunk.content,
                            "metadata": {
                                "paper_id": str(chunk.paper_id),
                                "page_number": chunk.page_number,
                                "chunk_index": chunk.chunk_index,
                                "user_id": str(user_id) if user_id else ""
                            }
                        })
                    
                    # Upsert in batches to avoid memory/rate limits
                    batch_size = 50
                    for i in range(0, len(qdrant_chunks), batch_size):
                        batch = qdrant_chunks[i:i+batch_size]
                        QdrantService.upsert_chunks(collection_name, batch)
                    logger.info("Qdrant sync completed successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database tables or sync Qdrant: {str(e)}")
    yield
    # Shutdown actions
    logger.info("Shutting down API server...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for RAG-based Research Paper Assistant",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS middleware
# In production, specify actual domain names for security
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for strict origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(papers.router, prefix=settings.API_V1_STR)
app.include_router(chat.router, prefix=settings.API_V1_STR)
app.include_router(chatbot.router, prefix=settings.API_V1_STR)
app.include_router(upload.router, prefix=settings.API_V1_STR)
app.include_router(rag.router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Root"])
async def root():
    """Welcome endpoint pointing to docs."""
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API",
        "docs": "/docs",
        "health": "/health",
        "version": "1.0.0"
    }


@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health"])
async def health_check():
    """Simple API status checker."""
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "version": "1.0.0"
    }
