import logging
from typing import Dict
from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from app.services.llm_service import get_llm_model

logger = logging.getLogger(__name__)

# Dictionary holding in-memory chat histories mapped to their session_id
session_histories: Dict[str, InMemoryChatMessageHistory] = {}


def get_session_history(session_id: str) -> BaseChatMessageHistory:
    """
    Retrieve or create the ChatMessageHistory object for a given session ID.
    
    Why: Manages isolated, session-based memories.
    Inputs: session_id (str)
    Outputs: BaseChatMessageHistory instance.
    """
    if session_id not in session_histories:
        session_histories[session_id] = InMemoryChatMessageHistory()
    return session_histories[session_id]


class AIService:
    """
    Service layer representing the conversational chatbot workflow.
    
    Why: Separates chat logic and session storage from routing.
    What: Instantiates chat prompts, binds history, and queries LLM.
    """
    
    @classmethod
    def get_chatbot_chain(cls) -> RunnableWithMessageHistory:
        """
        Builds the LangChain LCEL chain wrapped with message history.
        
        Why: Binds conversation history and prompt formatting together.
        Outputs: RunnableWithMessageHistory object.
        """
        # 1. Compile chat prompt template containing system instructions and chat history placeholder
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are a professional and polite AI assistant. "
                "Answer politely and use the previous conversation context to assist the user. "
                "If you cannot find details, answer appropriately."
            ),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{message}")
        ])
        
        # 2. Load the ChatGroq model
        llm = get_llm_model()
        
        # 3. Create prompt -> LLM pipeline
        chain = prompt | llm
        
        # 4. Wrap the chain with history management
        return RunnableWithMessageHistory(
            chain,
            get_session_history,
            input_messages_key="message",
            history_messages_key="history"
        )

    @classmethod
    async def chat(cls, session_id: str, message: str) -> str:
        """
        Send a message to the session chatbot and return the AI's answer.
        
        Inputs:
            - session_id (str): The unique session identifier.
            - message (str): User's query content.
        Outputs:
            - str: Generated assistant response.
        """
        if not session_id or not session_id.strip():
            raise ValueError("Invalid session ID.")
            
        if not message or not message.strip():
            raise ValueError("Empty message.")
            
        chain = cls.get_chatbot_chain()
        config = {"configurable": {"session_id": session_id}}
        
        # Run blocking langchain call in an async-friendly thread pool
        import asyncio
        try:
            response = await asyncio.to_thread(
                chain.invoke,
                {"message": message},
                config=config
            )
            return response.content.strip()
        except Exception as e:
            logger.error(f"Error in chatbot memory chain: {e}")
            raise RuntimeError(f"Chat execution failed: {str(e)}")
