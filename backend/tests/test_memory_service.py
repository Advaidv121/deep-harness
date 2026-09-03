import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, text
from backend.app.models import Base, Fact, Tombstone
from backend.app.schemas import MemoryManageRequest
from backend.app.services.memory_service import MemoryService, MemoryCapacityExceededError

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

@pytest.fixture
def memory_svc(tmp_path):
    svc = MemoryService()
    svc.user_md_path = tmp_path / "USER.md"
    svc.memory_md_path = tmp_path / "MEMORY.md"
    svc.user_md_path.write_text("# USER PROFILE\n", encoding="utf-8")
    svc.memory_md_path.write_text("# SHARED MEMORY\n", encoding="utf-8")
    return svc

@pytest.mark.asyncio
async def test_add_memory_and_bi_temporal_insert(memory_svc, test_db):
    req = MemoryManageRequest(
        action="add",
        target="MEMORY",
        content="Switched from espresso to matcha green tea.",
        category="diet",
        salience_score=0.9
    )
    res = await memory_svc.manage_memory(db=test_db, req=req, user_id="test_user")
    assert res.success is True
    assert "matcha green tea" in memory_svc.read_markdown("MEMORY")

    facts = await memory_svc.list_facts(db=test_db, user_id="test_user", active_only=True)
    assert len(facts) == 1
    assert facts[0].content == "Switched from espresso to matcha green tea."
    assert facts[0].is_active is True
    assert facts[0].valid_until is None

@pytest.mark.asyncio
async def test_capacity_exceeded_raises_error(memory_svc, test_db):
    # Try adding a massive string exceeding 2,200 chars
    huge_text = "A" * 2300
    req = MemoryManageRequest(
        action="add",
        target="MEMORY",
        content=huge_text,
        category="other"
    )
    with pytest.raises(MemoryCapacityExceededError) as exc_info:
        await memory_svc.manage_memory(db=test_db, req=req, user_id="test_user")
    assert "Consolidation required" in str(exc_info.value)

@pytest.mark.asyncio
async def test_replace_creates_tombstone_and_invalidates_fact(memory_svc, test_db):
    # 1. Add initial fact
    add_req = MemoryManageRequest(
        action="add",
        target="MEMORY",
        content="Loves double espresso in the morning.",
        category="diet"
    )
    await memory_svc.manage_memory(db=test_db, req=add_req, user_id="test_user")
    
    # 2. Replace with contradictory fact
    replace_req = MemoryManageRequest(
        action="replace",
        target="MEMORY",
        content="Quit all caffeine and now drinks herbal tea.",
        old_text="Loves double espresso in the morning.",
        category="diet"
    )
    replace_res = await memory_svc.manage_memory(db=test_db, req=replace_req, user_id="test_user")
    assert replace_res.success is True

    # 3. Verify Active Facts (only new one active)
    active_facts = await memory_svc.list_facts(db=test_db, user_id="test_user", active_only=True)
    assert len(active_facts) == 1
    assert "herbal tea" in active_facts[0].content

    # 4. Verify All Facts (including invalidated)
    all_facts = await memory_svc.list_facts(db=test_db, user_id="test_user", active_only=False)
    assert len(all_facts) == 2
    superseded = [f for f in all_facts if not f.is_active][0]
    assert "double espresso" in superseded.content
    assert superseded.valid_until is not None
    assert superseded.invalidated_at is not None

    # 5. Verify Tombstone was recorded
    tombstones = await memory_svc.list_tombstones(db=test_db, user_id="test_user")
    assert len(tombstones) == 1
    assert tombstones[0].fact_id == superseded.id
    assert tombstones[0].reason == "contradicted"

@pytest.mark.asyncio
async def test_remove_memory_item(memory_svc, test_db):
    add_req = MemoryManageRequest(
        action="add",
        target="USER",
        content="Loves vintage cars.",
        category="hobby"
    )
    await memory_svc.manage_memory(db=test_db, req=add_req, user_id="test_user")

    remove_req = MemoryManageRequest(
        action="remove",
        target="USER",
        old_text="Loves vintage cars."
    )
    await memory_svc.manage_memory(db=test_db, req=remove_req, user_id="test_user")
    assert "Loves vintage cars" not in memory_svc.read_markdown("USER")

    active_facts = await memory_svc.list_facts(db=test_db, user_id="test_user", active_only=True)
    assert len(active_facts) == 0

    tombstones = await memory_svc.list_tombstones(db=test_db, user_id="test_user")
    assert len(tombstones) == 1
    assert tombstones[0].reason == "manual_removal"
