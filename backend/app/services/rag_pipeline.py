import json
import logging
from typing import AsyncGenerator, List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Paper, DocumentChunk
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
        
        # 1. Fetch past messages to construct conversation history (limit to last 6 messages)
        past_messages = await conversation_repo.get_messages_by_conversation(conversation_id)
        chat_history = []
        for msg in past_messages[-6:]:
            if msg.role == "user":
                chat_history.append(HumanMessage(content=msg.content))
            else:
                chat_history.append(AIMessage(content=msg.content))

        # 2. Condense follow-up query if chat history exists
        search_query = question
        if chat_history:
            try:
                history_turns = []
                for msg in past_messages[-6:]:
                    role_label = "User" if msg.role == "user" else "Assistant"
                    history_turns.append(f"{role_label}: {msg.content}")
                history_str = "\n".join(history_turns)
                
                condense_prompt = (
                    "Given the following conversation history and a follow-up question, rephrase the follow-up question "
                    "to be a standalone question that can be searched in a vector database. "
                    "Do NOT answer the question, just return the rephrased standalone question in English. "
                    "If the follow-up question is already standalone and does not refer to history, return it as-is.\n\n"
                    "Chat History:\n"
                    f"{history_str}\n\n"
                    f"Follow-up Question: {question}\n"
                    "Standalone Question:"
                )
                condense_llm = get_llm_model(streaming=False)
                import asyncio
                res = await asyncio.to_thread(condense_llm.invoke, [HumanMessage(content=condense_prompt)])
                standalone_query = res.content.strip()
                if standalone_query.startswith('"') and standalone_query.endswith('"'):
                    standalone_query = standalone_query[1:-1]
                search_query = standalone_query
                logger.info(f"RAG: Condensed query from '{question}' to '{search_query}'")
            except Exception as ce:
                logger.warning(f"RAG: Failed to condense query: {ce}")

        # 3. Fetch relevant chunks from pgvector/Qdrant using search_query
        logger.info(f"RAG: Retrieving relevant context for question in chat {conversation_id}")
        search_results = await VectorService.similarity_search(
            db=db,
            query=search_query,
            user_id=user_id,
            paper_ids=paper_ids,
            limit=5
        )
        
        # 3b. Fetch paper records matching paper_ids (or matched via similarity search)
        papers = []
        if paper_ids:
            # Query db for specified papers
            stmt_papers = select(Paper).where(Paper.id.in_(paper_ids))
            res_papers = await db.execute(stmt_papers)
            papers = list(res_papers.scalars().all())
        else:
            # If no paper_ids are selected, we can fetch the papers that appeared in the search results
            matched_paper_ids = list(set([chunk.paper_id for chunk, paper, score in search_results]))
            if matched_paper_ids:
                stmt_papers = select(Paper).where(Paper.id.in_(matched_paper_ids))
                res_papers = await db.execute(stmt_papers)
                papers = list(res_papers.scalars().all())
                
        # Prepare papers metadata context string
        papers_meta_list = []
        for p in papers:
            authors_str = getattr(p, "authors", None) or "Unknown"
            papers_meta_list.append(
                f"Paper Title: {p.title}\n"
                f"File Name: {p.file_name}\n"
                f"Authors: {authors_str}\n"
                f"Abstract: {p.abstract or 'Not available.'}\n"
                f"Summary: {p.summary or 'Not available.'}"
            )
        papers_metadata_context = "\n\n---\n\n".join(papers_meta_list) if papers_meta_list else "No papers metadata available."
        
        # Also query the first page chunks for these papers to provide raw text header details (contains authors, titles)
        first_page_chunks = []
        if papers:
            paper_uuids = [p.id for p in papers]
            stmt_page1 = (
                select(DocumentChunk)
                .where(DocumentChunk.paper_id.in_(paper_uuids))
                .where(DocumentChunk.page_number == 1)
                .order_by(DocumentChunk.chunk_index)
            )
            res_page1 = await db.execute(stmt_page1)
            first_page_chunks = list(res_page1.scalars().all())
        
        # 4. Extract citations list & format context
        citations = []
        context_blocks = []
        
        # Prepend first page chunks as context to guarantee access to header metadata
        for chunk in first_page_chunks:
            paper = next((p for p in papers if p.id == chunk.paper_id), None)
            paper_title = paper.title if paper else "Unknown"
            context_blocks.append(
                f"Excerpt (Page 1 Header) | Source: {paper_title} (Page 1):\n{chunk.content}"
            )
            
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
        
        # 5. Formulate the LLM inputs
        context_str = "\n\n---\n\n".join(context_blocks) if context_blocks else "No relevant context found in documents."
        
        system_instructions = (
            "You are a professional Research Paper Assistant. Answer the user's question based strictly and ONLY on the provided retrieved excerpts and uploaded papers metadata.\n"
            "If the answer cannot be derived from the excerpts or papers metadata, reply: 'I'm sorry, but I cannot find that information in the uploaded research papers.' Do NOT make up facts or use outside knowledge.\n"
            "Citations format: In your explanation, explicitly cite which research paper and page number you are referring to when stating facts (e.g., 'According to [Paper Name] (Page X)...' or if referring to general paper metadata, 'According to the metadata of [Paper Name]...').\n\n"
            "Uploaded Papers Metadata:\n"
            f"{papers_metadata_context}\n\n"
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
            error_msg = f"\n\n[Error occurred during response generation: {str(e)}]"
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
