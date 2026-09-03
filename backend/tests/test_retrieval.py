import pytest
import pytest_asyncio
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
from backend.app.models import Base, Fact
from backend.app.services.retrieval import RetrievalService
from backend.app.services.embedding_service import embedding_service

@pytest_asyncio.fixture
async def test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(
                id UNINDEXED,
                user_id UNINDEXED,
                content,
                category
            );
        """))
    
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()

@pytest.mark.asyncio
async def test_hybrid_retrieval_and_rrf(test_db):
    retrieval_svc = RetrievalService(rrf_k=60, top_k=5)
    now = datetime.utcnow()

    # Insert Active Facts
    fact1_id = str(uuid.uuid4())
    vec1 = embedding_service.encode("Barnaby is a rescue golden retriever dog")
    f1 = Fact(
        id=fact1_id,
        user_id="user_1",
        category="relationship",
        content="Barnaby is a rescue golden retriever dog",
        salience_score=0.95,
        valid_from=now,
        valid_until=None,
        created_at=now,
        embedding=embedding_service.to_bytes(vec1)
    )
    test_db.add(f1)

    fact2_id = str(uuid.uuid4())
    vec2 = embedding_service.encode("Enjoys backpacking in Hokkaido Japan during autumn")
    f2 = Fact(
        id=fact2_id,
        user_id="user_1",
        category="travel",
        content="Enjoys backpacking in Hokkaido Japan during autumn",
        salience_score=0.85,
        valid_from=now,
        valid_until=None,
        created_at=now,
        embedding=embedding_service.to_bytes(vec2)
    )
    test_db.add(f2)

    # Insert Invalidated Fact (should NEVER be retrieved)
    fact3_id = str(uuid.uuid4())
    vec3 = embedding_service.encode("Drinks double espresso every morning")
    f3 = Fact(
        id=fact3_id,
        user_id="user_1",
        category="diet",
        content="Drinks double espresso every morning",
        salience_score=0.9,
        valid_from=now,
        valid_until=now,  # Superseded!
        invalidated_at=now,
        created_at=now,
        embedding=embedding_service.to_bytes(vec3)
    )
    test_db.add(f3)
    await test_db.flush()

    # Insert into FTS5
    await test_db.execute(
        text("INSERT INTO facts_fts (id, user_id, content, category) VALUES (:id, :user_id, :content, :category)"),
        {"id": fact1_id, "user_id": "user_1", "content": f1.content, "category": f1.category}
    )
    await test_db.execute(
        text("INSERT INTO facts_fts (id, user_id, content, category) VALUES (:id, :user_id, :content, :category)"),
        {"id": fact2_id, "user_id": "user_1", "content": f2.content, "category": f2.category}
    )
    await test_db.execute(
        text("INSERT INTO facts_fts (id, user_id, content, category) VALUES (:id, :user_id, :content, :category)"),
        {"id": fact3_id, "user_id": "user_1", "content": f3.content, "category": f3.category}
    )
    await test_db.commit()

    # Query matching dog
    results = await retrieval_svc.retrieve_active_facts(
        db=test_db,
        query="Tell me about my dog Barnaby",
        user_id="user_1",
        limit=5
    )

    assert len(results) > 0
    top_hit = results[0]
    assert "Barnaby" in top_hit["content"]
    assert top_hit["rrf_score"] > 0

    # Ensure invalidated fact is NOT retrieved even when directly queried
    espresso_results = await retrieval_svc.retrieve_active_facts(
        db=test_db,
        query="espresso morning coffee",
        user_id="user_1",
        limit=5
    )
    retrieved_contents = [r["content"] for r in espresso_results]
    assert not any("espresso" in c.lower() for c in retrieved_contents)
