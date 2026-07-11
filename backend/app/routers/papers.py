import os
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.auth import get_current_user
from app.schemas.schemas import (
    UserResponse, PaperResponse, PaperUpdate, SearchQuery, SearchResult, SummaryResponse
)
from app.repositories.paper_repository import PaperRepository
from app.services.storage_service import LocalStorageService
from app.services.vector_service import VectorService
from app.services.document_processor import process_pdf_background
from app.config import settings

router = APIRouter(prefix="/papers", tags=["Papers Management"])

storage_service = LocalStorageService()


async def run_process_pdf_background(paper_id: uuid.UUID, file_path: str, job_id: uuid.UUID):
    """Background task launcher that runs within its own database session."""
    async with AsyncSessionLocal() as db:
        await process_pdf_background(db, paper_id, file_path, job_id)


@router.post("/upload", response_model=List[PaperResponse], status_code=status.HTTP_202_ACCEPTED)
async def upload_papers(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload one or more PDF files, saving metadata and running parsing in the background."""
    paper_repo = PaperRepository(db)
    responses = []
    
    for file in files:
        # 1. Validate file format
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File {file.filename} is not a PDF."
            )
            
        # 2. Check file size (Read content to size check, reset position)
        content = await file.read()
        file_size = len(content)
        if file_size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File {file.filename} exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB}MB."
            )
            
        # 3. Save PDF file content
        file_path = await storage_service.save_file(file.filename, content)
        
        # 4. Save metadata to DB
        title = file.filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ")
        paper = await paper_repo.create(
            user_id=current_user.id,
            title=title,
            file_name=file.filename,
            file_path=file_path,
            file_size=file_size
        )
        
        # 5. Create processing job
        job = await paper_repo.create_job(paper.id)
        
        # 6. Trigger background parsing task
        background_tasks.add_task(run_process_pdf_background, paper.id, file_path, job.id)
        
        responses.append(paper)
        
    return responses


@router.get("", response_model=List[PaperResponse])
async def list_papers(
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve all uploaded papers for the logged-in user."""
    paper_repo = PaperRepository(db)
    return await paper_repo.list_by_user(current_user.id, skip=skip, limit=limit, search_query=search)


@router.get("/stats")
async def get_paper_stats(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get metrics summary (total uploaded papers) for the user's dashboard."""
    paper_repo = PaperRepository(db)
    total_papers = await paper_repo.count_by_user(current_user.id)
    return {"total_papers": total_papers}


@router.get("/{paper_id}", response_model=PaperResponse)
async def get_paper(
    paper_id: uuid.UUID,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Fetch details of a specific paper."""
    paper_repo = PaperRepository(db)
    paper = await paper_repo.get_by_id(paper_id, current_user.id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found or unauthorized.")
    return paper


@router.put("/{paper_id}", response_model=PaperResponse)
async def update_paper(
    paper_id: uuid.UUID,
    paper_update: PaperUpdate,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Rename a paper title."""
    paper_repo = PaperRepository(db)
    paper = await paper_repo.get_by_id(paper_id, current_user.id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found or unauthorized.")
    return await paper_repo.update(paper, paper_update)


@router.delete("/{paper_id}")
async def delete_paper(
    paper_id: uuid.UUID,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a paper record, its document chunks, and its saved file from storage."""
    paper_repo = PaperRepository(db)
    paper = await paper_repo.get_by_id(paper_id, current_user.id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found or unauthorized.")
        
    # Delete file from local storage
    await storage_service.delete_file(paper.file_path)
    
    # Delete DB records
    await paper_repo.delete(paper)
    return {"detail": "Paper deleted successfully"}


@router.get("/{paper_id}/download")
async def download_paper(
    paper_id: uuid.UUID,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Download the original PDF file."""
    paper_repo = PaperRepository(db)
    paper = await paper_repo.get_by_id(paper_id, current_user.id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found or unauthorized.")
        
    if not os.path.exists(paper.file_path):
        raise HTTPException(status_code=404, detail="Physical PDF file not found on storage server.")
        
    return FileResponse(
        path=paper.file_path,
        media_type="application/pdf",
        filename=paper.file_name
    )


@router.post("/search/semantic", response_model=List[SearchResult])
async def semantic_search(
    query_in: SearchQuery,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Search for relevant paper text segments across documents using pgvector similarity search."""
    search_results = await VectorService.similarity_search(
        db=db,
        query=query_in.query,
        user_id=current_user.id,
        paper_ids=query_in.paper_ids,
        limit=query_in.limit
    )
    
    formatted_results = []
    for chunk, paper, score in search_results:
        formatted_results.append(
            SearchResult(
                chunk_id=chunk.id,
                paper_id=paper.id,
                paper_title=paper.title,
                page_number=chunk.page_number,
                content=chunk.content,
                score=score
            )
        )
    return formatted_results


@router.get("/{paper_id}/summarize", response_model=SummaryResponse)
async def summarize_paper(
    paper_id: uuid.UUID,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve pre-computed summaries and simple explanation for a paper."""
    paper_repo = PaperRepository(db)
    paper = await paper_repo.get_by_id(paper_id, current_user.id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found or unauthorized.")
        
    if paper.status != "completed":
        raise HTTPException(status_code=400, detail="Paper processing is not completed yet.")
        
    # Compile explain simple fallback if needed
    explain_simple = None
    if paper.summary:
        # We can construct or fetch it
        # Since we stored it in the DB during background processing:
        # Wait, did we store explain_simple? In our models.py, summary, abstract, key_points are columns.
        # We can check if explain_simple is inside key_points or separate.
        # Let's generate it dynamically if not stored, or return abstract/summary.
        # To make it super robust, if we want an explain-like-I'm-5 explanation, we can generate it on-the-fly from the summary.
        # This is extremely useful if the user requests it!
        # Let's call the LLM to generate explain_simple from the paper's pre-computed summary.
        from app.services.llm_service import get_llm_model
        from langchain_core.messages import SystemMessage, HumanMessage
        try:
            llm = get_llm_model()
            messages = [
                SystemMessage(content="Explain the following summary of a research paper in extremely simple language, suitable for a 10-year-old. Keep it under 3 sentences."),
                HumanMessage(content=f"Summary: {paper.summary}")
            ]
            import asyncio
            response = await asyncio.to_thread(llm.invoke, messages)
            explain_simple = response.content.strip()
        except Exception:
            explain_simple = "Explain-like-I'm-5 explanation generation failed."
            
    return SummaryResponse(
        summary=paper.summary or "No summary generated.",
        abstract=paper.abstract or "No abstract available.",
        key_points=paper.key_points or [],
        explain_simple=explain_simple
    )
