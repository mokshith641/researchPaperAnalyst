from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.auth import get_current_user
from app.schemas.schemas import UserResponse
from app.schemas.rag import RAGSearchRequest, RAGSearchResponse, RAGAskRequest, RAGAskResponse
from app.services.rag_service import RAGService
from app.services.qdrant_service import QdrantService

# Define RAG router
router = APIRouter(prefix="/rag", tags=["Retrieval-Augmented Generation (RAG)"])

@router.post("/embed", status_code=status.HTTP_200_OK)
async def embed_database_records(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Read all document chunks in PostgreSQL, generate embeddings, and store them in Qdrant.
    
    Why: Syncs relational DB documents into the vector database.
    Inputs: None (implicitly current logged-in user via Dependency Injection).
    Outputs: Status object detailing how many chunks were indexed.
    """
    count = await RAGService.embed_all_records(db, current_user.id)
    return {"detail": f"Successfully indexed {count} document chunks into Qdrant."}


@router.post("/search", response_model=List[RAGSearchResponse], status_code=status.HTTP_200_OK)
async def semantic_search(
    request: RAGSearchRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Perform semantic vector similarity search against the Qdrant database.
    
    Inputs:
        - request (RAGSearchRequest): query and limit limit.
    Outputs:
        - List[RAGSearchResponse]: Top matches matching the query vector.
    """
    matches = await RAGService.search_similar_records(
        query=request.query,
        user_id=current_user.id,
        limit=request.limit
    )
    return matches


@router.post("/ask", response_model=RAGAskResponse, status_code=status.HTTP_200_OK)
async def ask_rag(
    request: RAGAskRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Perform Retrieval-Augmented Generation (RAG) using context fetched from Qdrant and the Groq LLM.
    
    Inputs:
        - request (RAGAskRequest): Question payload.
    Outputs:
        - RAGAskResponse: Generated answer text and reference citation objects.
    """
    result = await RAGService.ask_question(
        query=request.query,
        user_id=current_user.id,
        limit=request.limit
    )
    return result


@router.delete("/delete-all", status_code=status.HTTP_200_OK)
async def delete_rag_collection(
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Clear vector storage collection for development/cleanup purposes.
    """
    # Simply delete the collection
    success = QdrantService.delete_collection("research_papers")
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to drop collection from vector database."
        )
    return {"detail": "Vector collection cleared successfully."}
