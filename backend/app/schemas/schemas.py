from datetime import datetime
from typing import List, Optional, Any, Dict
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field

# --- User Schemas ---
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenRefreshRequest(BaseModel):
    refresh_token: str


# --- Paper Schemas ---
class PaperResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    file_name: str
    file_size: int
    status: str
    error_message: Optional[str] = None
    num_pages: Optional[int] = None
    summary: Optional[str] = None
    abstract: Optional[str] = None
    key_points: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PaperUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


# --- Document Chunk Schemas ---
class DocumentChunkResponse(BaseModel):
    id: UUID
    paper_id: UUID
    page_number: int
    chunk_index: int
    content: str

    class Config:
        from_attributes = True


# --- Chat/Message Schemas ---
class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1)

class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    citations: Optional[List[Dict[str, Any]]] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ConversationCreate(BaseModel):
    title: Optional[str] = None

class ConversationResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ConversationDetailResponse(ConversationResponse):
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True


# --- Semantic Search & Summarization Schemas ---
class SearchQuery(BaseModel):
    query: str = Field(..., min_length=1)
    paper_ids: Optional[List[UUID]] = None
    limit: int = Field(5, ge=1, le=50)

class SearchResult(BaseModel):
    chunk_id: UUID
    paper_id: UUID
    paper_title: str
    page_number: int
    content: str
    score: float

class SummaryResponse(BaseModel):
    summary: str
    abstract: Optional[str] = None
    key_points: List[str] = []
    explain_simple: Optional[str] = None
