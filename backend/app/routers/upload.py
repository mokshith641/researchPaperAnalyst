import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.routers.auth import get_current_user
from app.models.models import UploadedFile
from app.schemas.schemas import UserResponse
from app.schemas.upload import UploadResponse
from app.utils.file_validator import validate_file_upload
from app.services.s3_service import S3Service

# Create router for uploads
router = APIRouter(prefix="/upload", tags=["AWS S3 File Upload"])

@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a file (PDF, DOCX, or Image) to AWS S3 and record details in the database.
    
    Why: Central entry point for uploading user-owned assets.
    What: Reads, validates, uploads, and saves metadata.
    Inputs:
        - file (UploadFile): The binary file to upload.
    Outputs:
        - UploadResponse: The metadata of the successfully created database record.
    """
    # 1. Read file contents to calculate size
    content = await file.read()
    file_size = len(content)
    
    # 2. Validate file type and size
    validate_file_upload(file.filename, file_size)
    
    # 3. Upload to AWS S3 (or use fallback local directory)
    file_url = await S3Service.upload_file(file.filename, content)
    
    # 4. Save metadata to PostgreSQL database
    uploaded_file = UploadedFile(
        user_id=current_user.id,
        file_name=file.filename,
        file_url=file_url
    )
    db.add(uploaded_file)
    await db.commit()
    await db.refresh(uploaded_file)
    
    return uploaded_file


@router.get("/{file_id}", response_model=UploadResponse)
async def get_uploaded_file(
    file_id: uuid.UUID,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve details for an uploaded file by ID.
    
    Inputs:
        - file_id (UUID): The unique ID of the uploaded file.
    Outputs:
        - UploadResponse: Metadata of the file.
    """
    stmt = select(UploadedFile).where(
        UploadedFile.id == file_id,
        UploadedFile.user_id == current_user.id
    )
    result = await db.execute(stmt)
    uploaded_file = result.scalars().first()
    
    if not uploaded_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found or unauthorized."
        )
        
    return uploaded_file


@router.delete("/{file_id}")
async def delete_uploaded_file(
    file_id: uuid.UUID,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a file from storage and remove its entry from database.
    
    Inputs:
        - file_id (UUID): The unique ID of the uploaded file.
    Outputs:
        - dict: Success message confirmation.
    """
    stmt = select(UploadedFile).where(
        UploadedFile.id == file_id,
        UploadedFile.user_id == current_user.id
    )
    result = await db.execute(stmt)
    uploaded_file = result.scalars().first()
    
    if not uploaded_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found or unauthorized."
        )
        
    # 1. Delete physical file from storage (S3 or local fallback)
    await S3Service.delete_file(uploaded_file.file_url)
    
    # 2. Delete database metadata record
    await db.delete(uploaded_file)
    await db.commit()
    
    return {"detail": "File deleted successfully"}
