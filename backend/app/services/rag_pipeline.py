import json
import logging
from typing import AsyncGenerator, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.paper_repository import PaperRepository
from app.repositories.conversation_repository import ConversationRepository
from app.services.vector_service import VectorService
from app.services.llm_service import get_llm_model
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

logger = logging.getLogger(__name__)

class RAGPipeline:
    @classmethod
    async def chat_stream(
        cls,
        db: AsyncSession,
        user_id: UUID,
        conversation_id: UUID,
        question: str,
        paper_ids: Optional[List[UUID]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Executes similarity search, compiles prompt, and streams LLM answer.
        Yields JSON-formatted events: 'citations' or 'token' or 'done'.
        Logs messages asynchronously into database.
        """
        conversation_repo = ConversationRepository(db)
        
        # 1. Fetch relevant chunks from pgvector
        logger.info(f"RAG: Retrieving relevant context for question in chat {conversation_id}")
        search_results = await VectorService.similarity_search(
            db=db,
            query=question,
            user_id=user_id,
            paper_ids=paper_ids,
            limit=5
        )
        
        # 2. Extract citations list & format context
        citations = []
        context_blocks = []
        for idx, (chunk, paper, score) in enumerate(search_results):
            # Only include chunks with a reasonable similarity score (e.g. > 0.3)
            # cosine similarity score ranges from 0.0 to 1.0
            if score >= 0.2:
                citations.append({
                    "paper_id": str(paper.id),
                    "paper_title": paper.title,
                    "page_number": chunk.page_number,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content[:300] + "..."  # Snippet for citation UI
                })
                context_blocks.append(
                    f"Excerpt {idx+1} | Source: {paper.title} (Page {chunk.page_number}):\n{chunk.content}"
                )
                
        # Send citations event to client first
        yield f"event: citations\ndata: {json.dumps(citations)}\n\n"
        
        # 3. Fetch past messages to construct conversation history (limit to last 6 messages)
        past_messages = await conversation_repo.get_messages_by_conversation(conversation_id)
        chat_history = []
        for msg in past_messages[-6:]:
            if msg.role == "user":
                chat_history.append(HumanMessage(content=msg.content))
            else:
                chat_history.append(AIMessage(content=msg.content))
                
        # 4. Formulate the LLM inputs
        context_str = "\n\n---\n\n".join(context_blocks) if context_blocks else "No relevant context found in documents."
        
        system_instructions = (
            "You are a professional Research Paper Assistant. Answer the user's question based strictly and ONLY on the provided retrieved excerpts.\n"
            "If the answer cannot be derived from the excerpts, reply: 'I'm sorry, but I cannot find that information in the uploaded research papers.' Do NOT make up facts or use outside knowledge.\n"
            "Citations format: In your explanation, explicitly cite which research paper and page number you are referring to when stating facts (e.g., 'According to [Paper Name] (Page X)...').\n\n"
            "Retrieved Excerpts:\n"
            f"{context_str}"
        )
        
        messages = [SystemMessage(content=system_instructions)]
        messages.extend(chat_history)
        messages.append(HumanMessage(content=question))
        
        # 5. Save the user's message to database
        await conversation_repo.create_message(
            conversation_id=conversation_id,
            role="user",
            content=question
        )
        
        # 6. Call LLM with streaming enabled
        llm = get_llm_model(streaming=True)
        assistant_content = []
        
        try:
            logger.info("RAG: Invoking LLM streaming response")
            # Invoke streaming via async iterator
            # In LangChain, astream works asynchronously
            async for chunk in llm.astream(messages):
                token = chunk.content
                if token:
                    assistant_content.append(token)
                    # SSE format: event: token\ndata: "..." \n\n
                    # We escape newlines and double quotes to ensure valid json delivery
                    yield f"event: token\ndata: {json.dumps(token)}\n\n"
        except Exception as e:
            logger.error(f"RAG: LLM streaming error: {str(e)}")
            error_msg = "\n\n[Error occurred during response generation]"
            yield f"event: token\ndata: {json.dumps(error_msg)}\n\n"
            assistant_content.append(error_msg)
            
        full_answer = "".join(assistant_content)
        
        # 7. Save assistant's reply (with citations) to database
        await conversation_repo.create_message(
            conversation_id=conversation_id,
            role="assistant",
            content=full_answer,
            citations=citations
        )
        
        yield "event: done\ndata: [DONE]\n\n"
