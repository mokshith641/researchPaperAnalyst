import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Automatic fallback to local SQLite database if no database URL is set or if it points to the expired Supabase project
is_fallback = False
if not DATABASE_URL or "ehzneimxharlahkmvbii" in DATABASE_URL:
    logger.warning("Using local SQLite database (rpa.db) fallback for local development.")
    DATABASE_URL = "sqlite+aiosqlite:///./rpa.db"
    is_fallback = True

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Configure engine connection arguments based on driver
connect_args = {}
if "supabase.com" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.split("?")[0]
    connect_args = {
        "ssl": "require",
        "prepared_statement_cache_size": 0,
        "statement_cache_size": 0
    }
elif "postgresql" in DATABASE_URL:
    connect_args = {
        "prepared_statement_cache_size": 0,
        "statement_cache_size": 0
    }

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args=connect_args
)
SessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)
Base = declarative_base()

async def get_db():
    async with SessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()
# generator - uses yield and after it uses it can be used in try block 
# after the use it is closed
# prevents the memory leek , connection to db is closed properly
# it creates session for each request and closes it after the request
# ensures that each request has its own session