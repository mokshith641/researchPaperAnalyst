import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Conversation, Message

class ConversationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, conversation_id: uuid.UUID, user_id: Optional[uuid.UUID] = None) -> Optional[Conversation]:
        """Fetch a conversation and preload its message logs."""
        query = select(Conversation).where(Conversation.id == conversation_id)
        if user_id:
            query = query.where(Conversation.user_id == user_id)
        
        # Load messages collection in a single query
        query = query.options(selectinload(Conversation.messages))
        result = await self.db.execute(query)
        return result.scalars().first()

    async def list_by_user(self, user_id: uuid.UUID, skip: int = 0, limit: int = 50) -> List[Conversation]:
        """List active conversations for a user, sorted by last updated timestamp."""
        query = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(desc(Conversation.updated_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create(self, user_id: uuid.UUID, title: str) -> Conversation:
        """Create a new chat conversation session."""
        conversation = Conversation(
            user_id=user_id,
            title=title
        )
        self.db.add(conversation)
        await self.db.commit()
        await self.db.refresh(conversation)
        return conversation

    async def update_title(self, conversation_id: uuid.UUID, title: str, user_id: uuid.UUID) -> Optional[Conversation]:
        """Rename an existing conversation thread."""
        conversation = await self.get_by_id(conversation_id, user_id)
        if not conversation:
            return None
        conversation.title = title
        conversation.updated_at = datetime.utcnow()
        self.db.add(conversation)
        await self.db.commit()
        await self.db.refresh(conversation)
        return conversation

    async def delete(self, conversation: Conversation) -> bool:
        """Delete a conversation history."""
        await self.db.delete(conversation)
        await self.db.commit()
        return True

    # --- Message Operations ---
    async def create_message(
        self, conversation_id: uuid.UUID, role: str, content: str, citations: Optional[List[dict]] = None
    ) -> Message:
        """Insert a chat message log and bump the thread's updated timestamp."""
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            citations=citations
        )
        self.db.add(message)
        
        # Touch updated_at for conversation sorting
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalars().first()
        if conversation:
            conversation.updated_at = datetime.utcnow()
            self.db.add(conversation)
            
        await self.db.commit()
        await self.db.refresh(message)
        return message

    async def get_messages_by_conversation(self, conversation_id: uuid.UUID) -> List[Message]:
        """Fetch message logs for a conversation in ascending order (chronological)."""
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        return list(result.scalars().all())
