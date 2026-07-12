import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db, SessionLocal
from app.routers.auth import get_current_user
from app.schemas.schemas import (
    UserResponse, ConversationResponse, ConversationDetailResponse, MessageResponse
)
from app.repositories.conversation_repository import ConversationRepository
from app.services.rag_pipeline import RAGPipeline

router = APIRouter(prefix="/chat", tags=["AI Chat Workspace"])

class ChatRequest(BaseModel):
    content: str
    paper_ids: Optional[List[uuid.UUID]] = None


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Start a new chat session."""
    conversation_repo = ConversationRepository(db)
    # Default title
    title = "New Chat"
    return await conversation_repo.create(current_user.id, title)


@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    skip: int = 0,
    limit: int = 50,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List recent conversation sessions for the logged-in user."""
    conversation_repo = ConversationRepository(db)
    return await conversation_repo.list_by_user(current_user.id, skip=skip, limit=limit)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: uuid.UUID,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve full history (message logs) for a specific conversation."""
    conversation_repo = ConversationRepository(db)
    conversation = await conversation_repo.get_by_id(conversation_id, current_user.id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or unauthorized."
        )
    return conversation


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a conversation history."""
    conversation_repo = ConversationRepository(db)
    conversation = await conversation_repo.get_by_id(conversation_id, current_user.id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or unauthorized."
        )
    await conversation_repo.delete(conversation)
    return {"detail": "Conversation deleted successfully"}


class ConversationUpdate(BaseModel):
    title: str


@router.put("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: uuid.UUID,
    conversation_update: ConversationUpdate,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Rename an existing conversation thread."""
    conversation_repo = ConversationRepository(db)
    conversation = await conversation_repo.update_title(
        conversation_id, conversation_update.title, current_user.id
    )
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or unauthorized."
        )
    return conversation


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: uuid.UUID,
    request: ChatRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Submit a message to the conversation and receive a streaming Server-Sent Events (SSE) RAG response.
    Ensures safe async database connection handling during stream consumption.
    """
    # Verify the conversation exists and belongs to the user first
    async with SessionLocal() as init_db_session:
        conversation_repo = ConversationRepository(init_db_session)
        conversation = await conversation_repo.get_by_id(conversation_id, current_user.id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found or unauthorized."
            )
            
        # Update conversation title if it was the default "New Chat"
        if conversation.title == "New Chat":
            # Auto-title based on user prompt (first 30 characters)
            auto_title = request.content[:35] + ("..." if len(request.content) > 35 else "")
            await conversation_repo.update_title(conversation_id, auto_title, current_user.id)

    # Define SSE stream wrapper that holds onto its own isolated db connection
    async def sse_stream_generator():
        async with SessionLocal() as stream_db_session:
            async for chunk in RAGPipeline.chat_stream(
                db=stream_db_session,
                user_id=current_user.id,
                conversation_id=conversation_id,
                question=request.content,
                paper_ids=request.paper_ids
            ):
                yield chunk

    return StreamingResponse(
        sse_stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
