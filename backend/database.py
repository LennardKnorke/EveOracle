# backend/database.py

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

from config import DB_PASSWORD

DATABASE_URL = f"mysql+asyncmy://root:{DB_PASSWORD}@localhost:3306/eveoracle"

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    pool_recycle=3600
)

SessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False
)

Base = declarative_base()

async def get_db() -> AsyncSession:
    """
    Dependency function that yields a database session.
    FastAPI will automatically close the session when the request finishes.
    """
    async with SessionLocal() as session:
        yield session