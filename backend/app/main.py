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
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialization completed successfully.")
        
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


@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health"])
async def health_check():
    """Simple API status checker."""
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "version": "1.0.0"
    }
