import os
import boto3
import logging
from botocore.exceptions import NoCredentialsError, ClientError
from app.config import settings

logger = logging.getLogger(__name__)

class S3Service:
    """
    Service to manage AWS S3 interactions or fallback local directory operations.
    
    Why: Separates cloud storage logic from controllers.
    What: Handles upload, delete, and MIME-type detection.
    """
    
    @classmethod
    def get_s3_client(cls):
        """Initialize and return the S3 client if credentials are configured."""
        if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
            logger.warning("AWS credentials not configured. S3 operations will use local filesystem fallback.")
            return None
        try:
            return boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
        except Exception as e:
            logger.error(f"Failed to initialize boto3 S3 client: {e}")
            return None

    @classmethod
    async def upload_file(cls, file_name: str, file_content: bytes) -> str:
        """
        Uploads a file to AWS S3. Falls back to local directory if S3 is unconfigured.
        
        Inputs:
            - file_name (str): Original name of the file.
            - file_content (bytes): Raw file data in bytes.
        Outputs:
            - str: Publicly accessible URL of the uploaded file.
        """
        import uuid
        unique_name = f"{uuid.uuid4().hex}_{file_name}"
        client = cls.get_s3_client()
        
        if client and settings.AWS_BUCKET_NAME:
            try:
                # Run the blocking boto3 upload inside a thread pool
                import asyncio
                await asyncio.to_thread(
                    client.put_object,
                    Bucket=settings.AWS_BUCKET_NAME,
                    Key=unique_name,
                    Body=file_content,
                    ContentType=cls.get_content_type(file_name)
                )
                
                url = f"https://{settings.AWS_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{unique_name}"
                logger.info(f"Successfully uploaded {file_name} to S3: {url}")
                return url
            except NoCredentialsError:
                logger.error("AWS credentials missing during upload.")
            except ClientError as e:
                logger.error(f"S3 client error during upload: {e}")
                
        # FALLBACK: Save locally to upload directory and return local file URL mock
        logger.info("Using local fallback storage for upload.")
        local_path = os.path.join(settings.UPLOAD_DIR, unique_name)
        with open(local_path, "wb") as f:
            f.write(file_content)
        # Mock file URL for local dev
        return f"/uploads/{unique_name}"

    @classmethod
    async def delete_file(cls, file_url: str) -> bool:
        """
        Deletes a file from S3 (or local path if it was a fallback upload).
        
        Inputs:
            - file_url (str): The URL of the file to delete.
        Outputs:
            - bool: True if successfully deleted, False otherwise.
        """
        if file_url.startswith("/uploads/"):
            # Local fallback deletion
            file_name = file_url.replace("/uploads/", "")
            local_path = os.path.join(settings.UPLOAD_DIR, file_name)
            try:
                if os.path.exists(local_path):
                    os.remove(local_path)
                    return True
            except Exception as e:
                logger.error(f"Failed to delete local fallback file: {e}")
            return False
            
        client = cls.get_s3_client()
        if client and settings.AWS_BUCKET_NAME:
            try:
                # Extract key from URL
                key = file_url.split("amazonaws.com/")[-1]
                import asyncio
                await asyncio.to_thread(
                    client.delete_object,
                    Bucket=settings.AWS_BUCKET_NAME,
                    Key=key
                )
                logger.info(f"Successfully deleted {key} from S3.")
                return True
            except Exception as e:
                logger.error(f"Failed to delete file from S3: {e}")
        return False

    @staticmethod
    def get_content_type(file_name: str) -> str:
        """Return the proper MIME content type for S3 metadata."""
        ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
        mime_types = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png"
        }
        return mime_types.get(ext, "application/octet-stream")
