import uuid
from typing import List, Optional
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Paper, DocumentChunk, ProcessingJob
from app.schemas.schemas import PaperUpdate

class PaperRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, paper_id: uuid.UUID, user_id: Optional[uuid.UUID] = None) -> Optional[Paper]:
        """Get a paper by ID, optionally validating ownership by user_id."""
        query = select(Paper).where(Paper.id == paper_id)
        if user_id:
            query = query.where(Paper.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalars().first()

    async def list_by_user(
        self, user_id: uuid.UUID, skip: int = 0, limit: int = 20, search_query: Optional[str] = None
    ) -> List[Paper]:
        """List papers for a specific user, sorted by upload date descending."""
        query = select(Paper).where(Paper.user_id == user_id)
        if search_query:
            query = query.where(Paper.title.ilike(f"%{search_query}%"))
        query = query.order_by(desc(Paper.created_at)).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_by_user(self, user_id: uuid.UUID) -> int:
        """Count total uploaded papers for a user."""
        query = select(func.count(Paper.id)).where(Paper.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def create(self, user_id: uuid.UUID, title: str, file_name: str, file_path: str, file_size: int) -> Paper:
        """Initialize a new paper record in pending status."""
        db_paper = Paper(
            user_id=user_id,
            title=title,
            file_name=file_name,
            file_path=file_path,
            file_size=file_size,
            status="pending"
        )
        self.db.add(db_paper)
        await self.db.commit()
        await self.db.refresh(db_paper)
        return db_paper

    async def update(self, paper: Paper, update_schema: PaperUpdate) -> Paper:
        """Update paper metadata."""
        paper.title = update_schema.title
        self.db.add(paper)
        await self.db.commit()
        await self.db.refresh(paper)
        return paper

    async def update_status(
        self, paper_id: uuid.UUID, status: str, error_message: Optional[str] = None, num_pages: Optional[int] = None,
        summary: Optional[str] = None, abstract: Optional[str] = None, key_points: Optional[List[str]] = None
    ) -> Optional[Paper]:
        """Update processing status and extracted details for a paper."""
        paper = await self.get_by_id(paper_id)
        if not paper:
            return None
        
        paper.status = status
        if error_message:
            paper.error_message = error_message
        if num_pages is not None:
            paper.num_pages = num_pages
        if summary:
            paper.summary = summary
        if abstract:
            paper.abstract = abstract
        if key_points:
            paper.key_points = key_points
            
        self.db.add(paper)
        await self.db.commit()
        await self.db.refresh(paper)
        return paper

    async def delete(self, paper: Paper) -> bool:
        """Delete a paper record (cascades delete to chunks and jobs)."""
        await self.db.delete(paper)
        await self.db.commit()
        return True

    # --- Document Chunk Operations ---
    async def create_chunks(self, chunks: List[DocumentChunk]) -> None:
        """Bulk save document chunks with embeddings."""
        self.db.add_all(chunks)
        await self.db.commit()

    async def get_chunks_by_paper(self, paper_id: uuid.UUID) -> List[DocumentChunk]:
        """Retrieve all text chunks for a single paper."""
        result = await self.db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.paper_id == paper_id)
            .order_by(DocumentChunk.page_number, DocumentChunk.chunk_index)
        )
        return list(result.scalars().all())

    # --- Processing Job Operations ---
    async def create_job(self, paper_id: uuid.UUID) -> ProcessingJob:
        """Track document parsing work status."""
        job = ProcessingJob(paper_id=paper_id, status="pending")
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def update_job(self, job_id: uuid.UUID, status: str, error: Optional[str] = None) -> Optional[ProcessingJob]:
        """Update parsing job progress."""
        result = await self.db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))
        job = result.scalars().first()
        if not job:
            return None
        job.status = status
        job.error = error
        job.updated_at = func.now()
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job
