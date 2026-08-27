# backend/app/database/connection.py

from sqlalchemy.ext.asyncio import create_async_engine

from shared.config import settings


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,
    pool_recycle=3600
)