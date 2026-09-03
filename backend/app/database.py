import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
from backend.app.config import get_settings
from backend.app.models import Base

settings = get_settings()

DATABASE_URL = settings.database_url

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

async def init_db():
    # retry briefly if postgres not yet ready (docker startup race)
    for attempt in range(10):
        try:
            async with engine.begin() as conn:
                # pgvector + pg_trgm extensions (safe if already exists)
                try:
                    await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                except Exception:
                    pass
                try:
                    await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
                except Exception:
                    pass
                await conn.run_sync(Base.metadata.create_all)
                # Add tsvector column + GIN index if missing (idempotent)
                try:
                    await conn.execute(text("ALTER TABLE facts ADD COLUMN IF NOT EXISTS content_tsv tsvector"))
                except Exception:
                    pass
                try:
                    await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_facts_content_tsv ON facts USING GIN (content_tsv)"))
                except Exception:
                    pass
                # Backfill tsv for existing rows
                try:
                    await conn.execute(text("UPDATE facts SET content_tsv = to_tsvector('english', content) WHERE content_tsv IS NULL"))
                except Exception:
                    pass
            return
        except Exception as e:
            if attempt == 9:
                raise
            await asyncio.sleep(1.5)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
