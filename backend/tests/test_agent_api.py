import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.database import init_db

@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    await init_db()

@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "Deep Harness" in data["service"]

@pytest.mark.asyncio
async def test_memory_snapshot_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/memory/snapshot")
    assert response.status_code == 200
    data = response.json()
    assert "user_md" in data
    assert "memory_md" in data
    assert data["user_md_max"] == 1500
    assert data["memory_md_max"] == 2200

@pytest.mark.asyncio
async def test_chat_interaction_and_turn_persistence():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        chat_req = {
            "message": "Hey Sam! How are you doing today?",
            "user_id": "test_user_api",
            "session_id": "test_session_1"
        }
        response = await ac.post("/api/v1/chat", json=chat_req)
    assert response.status_code == 200
    data = response.json()
    assert len(data["response"]) > 0
    assert data["session_id"] == "test_session_1"
