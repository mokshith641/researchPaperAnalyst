from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

class UploadResponse(BaseModel):
    """
    Response schema representing metadata of an uploaded file.
    
    Why: Standardizes JSON responses returned by upload API routes.
    What: Exposes file identity, name, URL, and timestamp.
    """
    id: UUID
    user_id: UUID
    file_name: str
    file_url: str
    uploaded_at: datetime

    class Config:
        from_attributes = True
