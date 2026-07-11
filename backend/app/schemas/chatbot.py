from pydantic import BaseModel, Field

class ChatbotRequest(BaseModel):
    """Request schema for sending a message to the chatbot."""
    session_id: str = Field(..., description="Unique ID tracking the conversation history session.")
    message: str = Field(..., min_length=1, description="Text message to send to the chatbot.")

class ChatbotResponse(BaseModel):
    """Response schema returned by the chatbot."""
    reply: str = Field(..., description="AI generated chatbot response.")
