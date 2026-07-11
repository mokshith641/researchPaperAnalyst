import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO

from app.config import settings

class StorageService(ABC):
    @abstractmethod
    async def save_file(self, file_name: str, file_content: bytes) -> str:
        """Save a file and return its storage path/identifier."""
        pass

    @abstractmethod
    async def read_file(self, file_path: str) -> bytes:
        """Read and return a file's raw byte content."""
        pass

    @abstractmethod
    async def delete_file(self, file_path: str) -> bool:
        """Delete a file from the storage system."""
        pass


class LocalStorageService(StorageService):
    def __init__(self, upload_dir: str = settings.UPLOAD_DIR):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def save_file(self, file_name: str, file_content: bytes) -> str:
        # Prevent collisions by prefixing or formatting if needed, but unique folder per paper handles it
        import uuid
        unique_id = uuid.uuid4().hex
        file_path = self.upload_dir / f"{unique_id}_{file_name}"
        
        with open(file_path, "wb") as f:
            f.write(file_content)
            
        return str(file_path.absolute())

    async def read_file(self, file_path: str) -> bytes:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found at: {file_path}")
        with open(file_path, "rb") as f:
            return f.read()

    async def delete_file(self, file_path: str) -> bool:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception:
            return False


# In a real environment, you'd add SupabaseStorageService here
# calling supabase.storage.from_('bucket').upload(...)
