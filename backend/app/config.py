import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "Research Paper Assistant")
    API_V1_STR: str = os.getenv("API_V1_STR", "/api")

    # ---------------- Database ----------------
    DATABASE_URL: str = os.getenv("DATABASE_URL")

    # ---------------- Security ----------------
    JWT_SECRET: str = os.getenv("JWT_SECRET")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))

    # ---------------- Storage ----------------
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", 25))

    # ---------------- AI Stack ----------------
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "huggingface")
    HF_EMBEDDING_MODEL: str = os.getenv(
        "HF_EMBEDDING_MODEL",
        "sentence-transformers/all-MiniLM-L6-v2"
    )
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")

    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq")
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")

    # ---------------- Qdrant Vector DB ----------------
    QDRANT_URL: Optional[str] = os.getenv("QDRANT_URL")
    QDRANT_API_KEY: Optional[str] = os.getenv("QDRANT_API_KEY")

    # ---------------- AWS S3 Storage ----------------
    AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_BUCKET_NAME: Optional[str] = os.getenv("AWS_BUCKET_NAME")

    # ---------------- AI Models ----------------
    GROQ_MODEL_NAME: str = os.getenv(
        "GROQ_MODEL_NAME",
        "llama-3.3-70b-versatile"
    )
    OPENAI_MODEL_NAME: str = os.getenv(
        "OPENAI_MODEL_NAME",
        "gpt-4o-mini"
    )

    @property
    def vector_dimension(self) -> int:
        if self.EMBEDDING_PROVIDER == "openai":
            return 1536
        return 384

    @property
    def async_database_url(self) -> str:
        url = self.DATABASE_URL

        if "?" in url:
            base_url, query_params = url.split("?", 1)
            params = [
                p for p in query_params.split("&")
                if not p.startswith("sslmode")
            ]
            url = f"{base_url}?{'&'.join(params)}" if params else base_url

        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)

        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)

        return url

    class Config:
        case_sensitive = True
        env_file = ".env"


# Create single settings instance
settings = Settings()

# Ensure uploads directory exists
Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)