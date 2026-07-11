import logging
import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import DocumentChunk, Paper
from app.services.qdrant_service import QdrantService
from app.services.llm_service import get_llm_model
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)

# Collection identifier inside Qdrant
COLLECTION_NAME = "research_papers"


class RAGService:
    """
    RAG Orchestration Service.
    
    Why: Separates vector database loading, search, and LLM text generation logic.
    What: Indexes Postgres records in Qdrant and retrieves answers using Groq.
    """
    
    @classmethod
    async def embed_all_records(cls, db: AsyncSession, user_id: uuid.UUID) -> int:
        """
        Fetch document chunks from SQL database, generate vector embeddings, and save in Qdrant.
        
        Inputs:
            - db (AsyncSession): Database session.
            - user_id (UUID): Active user UUID to filter chunks.
        Outputs:
            - int: The number of chunks successfully embedded and indexed.
        """
        # 1. Fetch chunks owned by this user
        stmt = (
            select(DocumentChunk)
            .join(Paper, DocumentChunk.paper_id == Paper.id)
            .where(Paper.user_id == user_id)
        )
        result = await db.execute(stmt)
        chunks = result.scalars().all()
        
        if not chunks:
            logger.info(f"No database chunks found to embed for user {user_id}")
            return 0
            
        # 2. Format chunks for Qdrant upsert
        qdrant_chunks = []
        for chunk in chunks:
            qdrant_chunks.append({
                "id": chunk.id,
                "content": chunk.content,
                "metadata": {
                    "paper_id": str(chunk.paper_id),
                    "page_number": chunk.page_number,
                    "chunk_index": chunk.chunk_index,
                    "user_id": str(user_id)
                }
            })
            
        # 3. Upsert into Qdrant collection
        success = QdrantService.upsert_chunks(COLLECTION_NAME, qdrant_chunks)
        return len(chunks) if success else 0

    @classmethod
    async def search_similar_records(
        cls, query: str, user_id: uuid.UUID, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search against Qdrant collection, scoped by user_id filter.
        
        Inputs:
            - query (str): Text prompt to query.
            - user_id (UUID): Active user ID.
            - limit (int): Max matches count.
        Outputs:
            - List[Dict]: List of matching vector chunks.
        """
        filter_dict = {"user_id": str(user_id)}
        return QdrantService.search_similar(
            collection_name=COLLECTION_NAME,
            query=query,
            limit=limit,
            filter_dict=filter_dict
        )

    @classmethod
    async def ask_question(
        cls, query: str, user_id: uuid.UUID, limit: int = 5
    ) -> Dict[str, Any]:
        """
        Execute RAG: fetch Qdrant matches, construct context prompt, and query Groq LLM.
        
        Inputs:
            - query (str): User's natural language question.
            - user_id (UUID): Active user ID.
            - limit (int): Max context search results.
        Outputs:
            - Dict: Keys 'answer' (str) and 'citations' (List).
        """
        # 1. Fetch relevant context matches from Qdrant
        matches = await cls.search_similar_records(query, user_id, limit)
        
        # 2. Compile context excerpt block and citation structures
        context_blocks = []
        citations = []
        for idx, match in enumerate(matches):
            context_blocks.append(f"Excerpt {idx+1} (Page {match['metadata'].get('page_number')}):\n{match['content']}")
            citations.append({
                "chunk_id": str(match["id"]),
                "score": match["score"],
                "paper_id": match["metadata"].get("paper_id"),
                "page_number": match["metadata"].get("page_number")
            })
            
        context_str = "\n\n".join(context_blocks) if context_blocks else "No relevant context found."
        
        # 3. Compile System prompt template with context
        system_prompt = (
            "You are an intelligent assistant.\n"
            "Answer the user's question using ONLY the provided retrieved context. "
            "If the answer cannot be found in the context, politely respond that no "
            "relevant information was found in your research papers. Do not make up facts.\n\n"
            f"Retrieved Context:\n{context_str}"
        )
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=query)
        ]
        
        # 4. Invoke LLM
        llm = get_llm_model()
        try:
            import asyncio
            response = await asyncio.to_thread(llm.invoke, messages)
            answer = response.content.strip()
        except Exception as e:
            logger.error(f"Error querying LLM in RAG pipeline: {e}")
            answer = f"Error generating answer: {str(e)}"
            
        return {
            "answer": answer,
            "citations": citations
        }
