import logging
import uuid
import traceback
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.paper_repository import PaperRepository
from app.services.pdf_service import PDFService
from app.services.vector_service import VectorService
from app.services.llm_service import LLMService
from app.models.models import DocumentChunk

logger = logging.getLogger(__name__)

async def process_pdf_background(
    db: AsyncSession,
    paper_id: uuid.UUID,
    file_path: str,
    job_id: uuid.UUID
) -> None:
    """Extract, chunk, embed, and summarize a research paper in a background task."""
    paper_repo = PaperRepository(db)
    
    # Update job and paper status to processing
    await paper_repo.update_job(job_id, "processing")
    await paper_repo.update_status(paper_id, "processing")
    
    try:
        # 1. Extract text from PDF
        logger.info(f"Extracting text from PDF for paper {paper_id}")
        pages = PDFService.extract_text_by_page(file_path)
        num_pages = len(pages)
        
        if num_pages == 0:
            raise ValueError("No text could be extracted from this PDF. It might be scanned or empty.")

        # 2. Chunk text page-by-page
        logger.info(f"Chunking pages for paper {paper_id}")
        chunks_data = PDFService.chunk_pages(pages)
        
        if not chunks_data:
            raise ValueError("No text chunks generated.")

        # 3. Generate embeddings for each chunk in batches
        logger.info(f"Generating embeddings for {len(chunks_data)} chunks for paper {paper_id}")
        chunk_contents = [c["content"] for c in chunks_data]
        
        # Batch generation to avoid rate limits/timeouts
        embeddings = []
        batch_size = 32
        for i in range(0, len(chunk_contents), batch_size):
            batch_texts = chunk_contents[i:i+batch_size]
            batch_embeddings = await VectorService.get_embeddings(batch_texts)
            embeddings.extend(batch_embeddings)

        # 4. Save chunks to SQL DB and index in Qdrant
        logger.info(f"Saving chunks for paper {paper_id} to database")
        
        dialect_name = db.bind.dialect.name if db.bind else ""
        is_postgres = "postgresql" in dialect_name
        
        # Load paper to get owner metadata
        paper = await paper_repo.get_by_id(paper_id)
        user_id = paper.user_id if paper else None
        
        db_chunks = []
        for idx, chunk in enumerate(chunks_data):
            db_chunk = DocumentChunk(
                paper_id=paper_id,
                page_number=chunk["page_number"],
                chunk_index=chunk["chunk_index"],
                content=chunk["content"],
                embedding=embeddings[idx] if is_postgres else None
            )
            db_chunks.append(db_chunk)
            
        await paper_repo.create_chunks(db_chunks)
        
        # 4b. Index into Qdrant for semantic search fallback and RAG ask endpoints
        from app.services.qdrant_service import QdrantService
        qdrant_chunks = []
        for chunk in db_chunks:
            qdrant_chunks.append({
                "id": chunk.id,
                "content": chunk.content,
                "metadata": {
                    "paper_id": str(paper_id),
                    "page_number": chunk.page_number,
                    "chunk_index": chunk.chunk_index,
                    "user_id": str(user_id) if user_id else ""
                }
            })
        QdrantService.upsert_chunks("research_papers", qdrant_chunks)

        # 5. Summarize paper using LLM
        # We extract first 2 pages and last page to get abstract, introduction, and conclusion
        logger.info(f"Generating AI summary for paper {paper_id}")
        summary_source_text = ""
        first_pages = pages[:2]
        summary_source_text += "\n".join([p["text"] for p in first_pages])
        
        if num_pages > 2:
            summary_source_text += "\n\n" + pages[-1]["text"]
            
        # Truncate text context to prevent token overflows (approx 12000 chars is ~3000 tokens)
        summary_source_text = summary_source_text[:12000]
        
        summary_data = await LLMService.summarize_text(summary_source_text)

        # 6. Update paper metadata & status to completed
        await paper_repo.update_status(
            paper_id=paper_id,
            status="completed",
            num_pages=num_pages,
            summary=summary_data.get("summary"),
            abstract=summary_data.get("abstract"),
            key_points=summary_data.get("key_points"),
            authors=summary_data.get("authors")
        )
        
        # Update job status
        await paper_repo.update_job(job_id, "completed")
        logger.info(f"Successfully processed paper {paper_id}")
        
    except Exception as e:
        error_msg = f"Error processing PDF: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        
        # Update statuses to failed
        await paper_repo.update_status(paper_id, "failed", error_message=error_msg)
        await paper_repo.update_job(job_id, "failed", error=error_msg)
