from fastapi import APIRouter, HTTPException, status
from app.schemas.chatbot import ChatbotRequest, ChatbotResponse
from app.services.ai_service import AIService

# Define chatbot router
router = APIRouter(tags=["AI Chatbot"])

@router.post("/chat", response_model=ChatbotResponse, status_code=status.HTTP_200_OK)
async def chat_session(request: ChatbotRequest):
    """
    Submit a message to the AI Chatbot with session memory and receive a reply.
    
    Why: Binds conversation logic to standard API endpoints.
    Inputs:
        - request (ChatbotRequest): session ID and message text.
    Outputs:
        - ChatbotResponse: The generated reply.
    """
    try:
        reply = await AIService.chat(
            session_id=request.session_id,
            message=request.message
        )
        return ChatbotResponse(reply=reply)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
