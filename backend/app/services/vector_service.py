import asyncio
from typing import List, Optional, Tuple
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.models.models import DocumentChunk, Paper

# Cache the embedding model to avoid reloading on every request
_embeddings_model = None

def get_embeddings_model():
    """Load the embeddings model based on environment configuration."""
    global _embeddings_model
    if _embeddings_model is not None:
        return _embeddings_model

    if settings.EMBEDDING_PROVIDER == "openai":
        from langchain_openai import OpenAIEmbeddings
        # Assumes OPENAI_API_KEY is in environment variables or config
        _embeddings_model = OpenAIEmbeddings(
            openai_api_key=settings.OPENAI_API_KEY,
            model="text-embedding-3-small"
        )
    else:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        _embeddings_model = HuggingFaceEmbeddings(
            model_name=settings.HF_EMBEDDING_MODEL,
            encode_kwargs={'normalize_embeddings': True}
        )
    return _embeddings_model


class VectorService:
    @staticmethod
    async def get_embedding(text: str) -> List[float]:
        """Generate vector embedding for a single text string."""
        model = get_embeddings_model()
        # Embed single text (run in thread pool to prevent blocking)
        embeddings = await asyncio.to_thread(model.embed_query, text)
        return embeddings

    @staticmethod
    async def get_embeddings(texts: List[str]) -> List[List[float]]:
        """Generate vector embeddings for a list of text strings."""
        model = get_embeddings_model()
        # Embed multiple documents (run in thread pool to prevent blocking)
        embeddings = await asyncio.to_thread(model.embed_documents, texts)
        return embeddings

    @classmethod
    async def similarity_search(
        cls,
        db: AsyncSession,
        query: str,
        user_id: uuid.UUID,
        paper_ids: Optional[List[uuid.UUID]] = None,
        limit: int = 5
    ) -> List[Tuple[DocumentChunk, Paper, float]]:
        """Perform pgvector similarity search on chunks owned by user."""
        # 1. Fallback to Qdrant if using SQLite database
        dialect_name = db.bind.dialect.name if db.bind else ""
        is_postgres = "postgresql" in dialect_name
        
        if not is_postgres:
            from app.services.qdrant_service import QdrantService
            # Scoped by user_id payload filter
            filter_dict = {"user_id": str(user_id)}
            matches = QdrantService.search_similar("research_papers", query, limit, filter_dict)
            
            search_results = []
            for match in matches:
                chunk_id = uuid.UUID(match["id"])
                # Query DB for this chunk and its associated paper
                stmt = select(DocumentChunk, Paper).join(Paper).where(DocumentChunk.id == chunk_id)
                if paper_ids:
                    stmt = stmt.where(Paper.id.in_(paper_ids))
                res = await db.execute(stmt)
                row = res.first()
                if row:
                    chunk, paper = row
                    score = match["score"]
                    search_results.append((chunk, paper, score))
            return search_results

        # 2. Original pgvector search
        query_embedding = await cls.get_embedding(query)
        
        # Calculate cosine distance (pgvector operator)
        distance = DocumentChunk.embedding.cosine_distance(query_embedding)
        
        # Join with Paper table to check user_id and fetch paper metadata
        stmt = (
            select(DocumentChunk, Paper, distance.label("distance"))
            .join(Paper, DocumentChunk.paper_id == Paper.id)
            .where(Paper.user_id == user_id)
        )
        
        # Filter by specific papers if requested
        if paper_ids:
            stmt = stmt.where(Paper.id.in_(paper_ids))
            
        stmt = stmt.order_by("distance").limit(limit)
        
        result = await db.execute(stmt)
        search_results = []
        for row in result.all():
            chunk, paper, dist = row
            # Cosine similarity score = 1 - cosine distance
            score = 1.0 - float(dist)
            search_results.append((chunk, paper, score))
            
        return search_results
