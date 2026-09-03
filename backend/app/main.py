import json
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.database import init_db, get_db
from backend.app.schemas import (
    ChatMessageRequest, ChatMessageResponse, MemoryManageRequest,
    MemoryOperationResponse, MemorySnapshotResponse, FactResponse, TombstoneResponse,
    ProfileCreate, ProfileResponse
)
from backend.app.services.memory_service import memory_service, MemoryCapacityExceededError
from backend.app.agent import companion_agent
from backend.app.auth import authenticate, create_token, LoginRequest, LoginResponse, require_auth

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # best-effort Qdrant collection init (non-blocking for Postgres boot)
    try:
        from backend.app.services.qdrant_service import qdrant_service
        qdrant_service.ensure_collection()
    except Exception:
        pass
    yield

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION, lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ─── Auth routes (public) ───────────────────────────────────────────
@app.post("/auth/login", response_model=LoginResponse, tags=["Auth"])
async def login(req: LoginRequest):
    user = authenticate(req.username, req.password)
    token = create_token(req.username)
    return LoginResponse(
        token=token,
        username=req.username,
        display_name=user["display_name"],
        role=user["role"],
    )

@app.get("/auth/me", tags=["Auth"])
async def get_current_user(user=Depends(require_auth)):
    return user

# ─── Protected routes ───────────────────────────────────────────────
# Profiles (DB-backed, replaces localStorage-only)
DEFAULT_PROFILES_SEED = [
    {"id": "alex_prod", "name": "Alex", "role": "Senior Distributed Systems Engineer", "location": "San Francisco, CA", "avatar_bg": "from-sky-500 to-indigo-600"},
    {"id": "clara_orbital", "name": "Clara", "role": "Orbital Mechanics Researcher", "location": "Tokyo / Denver", "avatar_bg": "from-purple-500 to-pink-600"},
    {"id": "maya_architect", "name": "Maya", "role": "Sustainable Architect", "location": "Chicago, IL", "avatar_bg": "from-emerald-500 to-teal-600"},
]

@app.get("/api/v1/profiles", response_model=list[ProfileResponse], tags=["Profiles"])
async def list_profiles(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from backend.app.models import Profile
    result = await db.execute(select(Profile).order_by(Profile.created_at))
    profiles = result.scalars().all()
    # Auto-seed defaults if table empty
    if not profiles:
        for p in DEFAULT_PROFILES_SEED:
            db.add(Profile(**p))
        await db.commit()
        result = await db.execute(select(Profile).order_by(Profile.created_at))
        profiles = result.scalars().all()
    return profiles

@app.post("/api/v1/profiles", response_model=ProfileResponse, tags=["Profiles"])
async def create_profile(req: ProfileCreate, db: AsyncSession = Depends(get_db)):
    import uuid
    from backend.app.models import Profile
    pid = f"user_{req.name.lower().replace(' ', '_').replace('-', '_')[:20]}_{uuid.uuid4().hex[:4]}"
    # sanitize id
    pid = "".join(c if c.isalnum() or c in "_-" else "_" for c in pid)
    profile = Profile(id=pid, name=req.name.strip(), role=req.role.strip() or "Software Engineer", location=req.location.strip() or "Remote", avatar_bg=req.avatar_bg)
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile

@app.get("/api/v1/health", tags=["System"])
async def health_check():
    return {"status": "ok", "service": settings.PROJECT_NAME, "version": settings.VERSION, "environment": settings.ENVIRONMENT}

@app.get("/api/v1/memory/snapshot", response_model=MemorySnapshotResponse, tags=["Memory"])
async def get_memory_snapshot(user_id: str = "default_user"):
    snapshot = memory_service.get_snapshot(user_id=user_id)
    return MemorySnapshotResponse(**snapshot)

@app.post("/api/v1/memory/manage", response_model=MemoryOperationResponse, tags=["Memory"])
async def manage_memory(req: MemoryManageRequest, db: AsyncSession = Depends(get_db)):
    try:
        res = await memory_service.manage_memory(db=db, req=req, user_id=req.user_id)
        return res
    except MemoryCapacityExceededError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "MemoryCapacityExceeded", "message": str(e), "target": e.target, "current_chars": e.current_chars, "attempted_chars": e.attempted_chars, "max_chars": e.max_chars, "current_content": e.current_content})
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.get("/api/v1/facts", response_model=list[FactResponse], tags=["Memory"])
async def get_facts(active_only: bool = False, user_id: str = "default_user", db: AsyncSession = Depends(get_db)):
    return await memory_service.list_facts(db=db, active_only=active_only, user_id=user_id)

@app.get("/api/v1/tombstones", response_model=list[TombstoneResponse], tags=["Memory"])
async def get_tombstones(user_id: str = "default_user", db: AsyncSession = Depends(get_db)):
    return await memory_service.list_tombstones(db=db, user_id=user_id)

@app.get("/api/v1/memory/retrieve", tags=["Memory"])
async def query_retrieval(query: str, user_id: str = "default_user", limit: int = 10, db: AsyncSession = Depends(get_db)):
    from backend.app.services.retrieval import retrieval_service
    return await retrieval_service.retrieve_active_facts(db=db, query=query, user_id=user_id, limit=limit)

@app.post("/api/v1/memory/seed", tags=["Memory"])
async def seed_sample_profiles(user_id: str = "alex_prod", db: AsyncSession = Depends(get_db)):
    from backend.app.schemas import MemoryManageRequest
    seeds = {
        "alex_prod": [
            ("Works as Senior Distributed Systems Engineer on low-latency event sourcing engine", "career"),
            ("Lives in San Francisco, CA and hikes in Marin Headlands", "preference"),
            ("Has a rescue golden retriever named Barnaby", "relationship"),
            ("Switched from double espresso to matcha green tea in mornings", "health"),
            ("Planning a backpacking trip to Hokkaido in autumn", "travel"),
            ("Strictly avoiding refined sugar and syrups based on doctor lab results", "health")
        ],
        "clara_orbital": [
            ("Works as an orbital mechanics researcher in Denver, Colorado", "career"),
            ("Severely allergic to peanuts and tree nuts", "health"),
            ("Has a 5-year-old orange tabby cat named Copernicus", "relationship"),
            ("Loves bouldering and brewing pour-over coffee with Ethiopian beans", "hobby"),
            ("Prefers rainy mornings for deep focused research", "preference")
        ],
        "maya_architect": [
            ("Works as a sustainable architect in Chicago, IL", "career"),
            ("Adopted two Siamese kittens named Luna and Milo", "relationship"),
            ("Designs passive solar timber buildings and green roofs", "career"),
            ("Drinks oat milk flat whites and cycles along Lake Michigan", "hobby")
        ]
    }
    target_seeds = seeds.get(user_id, seeds["alex_prod"])
    created = []
    for content, category in target_seeds:
        try:
            res = await memory_service.manage_memory(
                db=db,
                req=MemoryManageRequest(
                    action="add",
                    target="MEMORY",
                    content=content,
                    category=category,
                    salience_score=0.95
                ),
                user_id=user_id
            )
            created.append(content)
        except Exception:
            pass
    return {"status": "ok", "seeded_user": user_id, "facts_added": len(created), "facts": created}

@app.post("/api/v1/chat", response_model=ChatMessageResponse, tags=["Chat"])
async def chat_sync(req: ChatMessageRequest, db: AsyncSession = Depends(get_db)):
    retrieved_facts = []
    tokens = []
    extracted = []
    memory_upd = False
    async for event in companion_agent.stream_turn(db=db, user_message=req.message, user_id=req.user_id, session_id=req.session_id or "default_session"):
        if event["type"] == "context":
            retrieved_facts = event.get("retrieved_facts", [])
        elif event["type"] == "token":
            tokens.append(event["token"])
        elif event["type"] == "done":
            extracted = event.get("extracted_facts", [])
            memory_upd = event.get("memory_updated", False)
    return ChatMessageResponse(response="".join(tokens), session_id=req.session_id or "default_session", retrieved_facts=retrieved_facts, extracted_facts=extracted, memory_updated=memory_upd)

@app.post("/api/v1/chat/stream", tags=["Chat"])
async def chat_stream(req: ChatMessageRequest, db: AsyncSession = Depends(get_db)):
    async def event_generator() -> AsyncGenerator[str, None]:
        async for event in companion_agent.stream_turn(db=db, user_message=req.message, user_id=req.user_id, session_id=req.session_id or "default_session"):
            yield json.dumps(event)
    return EventSourceResponse(event_generator())
