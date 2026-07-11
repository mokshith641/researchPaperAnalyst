import os
from fastapi import HTTPException, status
from app.config import settings

# Allowed file extensions for S3 uploads
ALLOWED_EXTENSIONS = {
    # Images
    "jpg", "jpeg", "png",
    # Documents
    "pdf", "docx"
}

def validate_file_upload(file_name: str, file_size: int) -> None:
    """
    Validates the file format and file size before uploading to S3.
    
    Why: Prevents users from uploading unsupported file types or extremely large files.
    What: Checks extension and size against configured settings.
    Inputs:
        - file_name (str): The name of the file to check.
        - file_size (int): Size of the file in bytes.
    Outputs:
        - None. Raises HTTPException if validation fails.
    """
    # 1. Validate file extension
    ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: .{ext}. Allowed formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
        
    # 2. Check for empty files
    if file_size <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File cannot be empty."
        )

    # 3. Check for file size limit
    max_size_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if file_size > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB}MB."
        )
