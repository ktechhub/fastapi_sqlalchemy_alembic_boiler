from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from ..core.config import settings
from ..core.loggers import db_logger as logger

# Use the dynamically set DATABASE_URL
DATABASE_URL = settings.DATABASE_URL

# Adjust engine options for SQLite
engine_options = {}
if "sqlite" not in DATABASE_URL:
    engine_options = {
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_pre_ping": True,
    }

# Create the engine with appropriate options
engine = create_async_engine(DATABASE_URL, **engine_options)

# Configure the sessionmaker
AsyncSessionLocal = sessionmaker(
    engine,
    autocommit=False,
    autoflush=False,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
