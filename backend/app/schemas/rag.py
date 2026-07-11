from typing import List, Dict, Any, Optional
from uuid import UUID
from pydantic import BaseModel, Field

class RAGSearchRequest(BaseModel):
    """Request schema for performing vector semantic search."""
    query: str = Field(..., min_length=1, description="The query string to search for semantically.")
    limit: int = Field(default=5, ge=1, le=50, description="Maximum number of context results to return.")

class RAGSearchResponse(BaseModel):
    """Response schema representing a single semantic search match."""
    id: str
    score: float
    content: str
    metadata: Dict[str, Any]

class RAGAskRequest(BaseModel):
    """Request schema for asking RAG questions."""
    query: str = Field(..., min_length=1, description="Question content.")
    limit: int = Field(default=5, ge=1, le=50, description="Context document limit.")

class RAGAskResponse(BaseModel):
    """Response schema for RAG answer generation."""
    answer: str
    citations: List[Dict[str, Any]]
