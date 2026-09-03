import uuid
from datetime import datetime
from typing import AsyncGenerator, List, Dict, Any, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.config import get_settings
from backend.app.models import Turn
from backend.app.schemas import MemoryManageRequest, ExtractedFact
from backend.app.services.memory_service import MemoryService, memory_service, MemoryCapacityExceededError
from backend.app.services.retrieval import retrieval_service
from backend.app.services.llm_service import llm_service

settings = get_settings()

class CompanionAgent:
    def __init__(self, memory_svc: Optional[MemoryService] = None):
        self.memory_svc = memory_svc or memory_service
        self.persona_path = settings.MEMORY_DIR / "persona.md"

    def read_persona(self) -> str:
        if self.persona_path.exists():
            return self.persona_path.read_text(encoding="utf-8")
        return "You are Sam, an empathetic and persistent AI companion."

    def build_system_prompt(self, user_md: str, memory_md: str, retrieved_facts: List[Dict[str, Any]]) -> str:
        """
        Builds the prompt with strict prefix hierarchy:
        1. [STATIC PREFIX - CACHED] Persona & Core Guidelines
        2. [DYNAMIC CONTEXT] Curated Memory Snapshot (USER.md + MEMORY.md)
        3. [PROACTIVE RETRIEVAL] Top-K Bi-temporal Active Facts
        """
        persona = self.read_persona().strip()
        
        facts_text = ""
        if retrieved_facts:
            facts_text = "\n### Proactively Retrieved Active Facts:\n" + "\n".join(
                f"- [{f.get('category', 'general').upper()}] {f['content']}" for f in retrieved_facts
            )

        prompt = f"""{persona}

---
## MEMORY SNAPSHOT (Current Ground Truth)
### USER.md (Bounded User Profile)
{user_md}

### MEMORY.md (Bounded Shared Context)
{memory_md}
{facts_text}

---
## INSTRUCTION:
Respond authentically as Sam. Respect all current facts and NEVER contradict or use outdated habits.
"""
        return prompt

    async def get_recent_turns(
        self,
        db: AsyncSession,
        session_id: str,
        limit: int = 10
    ) -> List[Turn]:
        stmt = select(Turn).where(Turn.session_id == session_id).order_by(Turn.turn_index.asc())
        result = await db.execute(stmt)
        turns = result.scalars().all()
        return turns[-limit:] if turns else []

    async def stream_turn(
        self,
        db: AsyncSession,
        user_message: str,
        user_id: str = "default_user",
        session_id: str = "default_session"
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Executes a streaming companion turn:
        1. Proactively retrieves bi-temporally active facts via FTS5 + Dense Vector RRF.
        2. Records user turn.
        3. Streams conversational response tokens.
        4. Saves assistant turn.
        5. Asynchronously extracts durable facts & updates bi-temporal store.
        """
        # 1. Proactive Hybrid Retrieval
        retrieved_facts = await retrieval_service.retrieve_active_facts(
            db=db,
            query=user_message,
            user_id=user_id,
            limit=settings.TOP_K_RETRIEVAL
        )

        # 2. Snapshot Bounded Memory
        snapshot = self.memory_svc.get_snapshot(user_id=user_id)
        system_prompt = self.build_system_prompt(
            user_md=snapshot["user_md"],
            memory_md=snapshot["memory_md"],
            retrieved_facts=retrieved_facts
        )

        # Fetch recent turns for dialogue buffer
        recent_turns = await self.get_recent_turns(db, session_id=session_id, limit=6)
        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
        
        for t in recent_turns:
            messages.append({"role": t.role, "content": t.content})
            
        messages.append({"role": "user", "content": user_message})

        # Save user turn to DB
        turn_index = len(recent_turns) + 1
        user_turn_id = str(uuid.uuid4())
        db_user_turn = Turn(
            id=user_turn_id,
            session_id=session_id,
            user_id=user_id,
            turn_index=turn_index,
            role="user",
            content=user_message,
            created_at=datetime.utcnow()
        )
        db.add(db_user_turn)
        await db.commit()

        # Yield retrieved context metadata first
        yield {
            "type": "context",
            "retrieved_facts": [f["content"] for f in retrieved_facts],
            "snapshot": snapshot
        }

        # 3. Stream Response Tokens
        assistant_chunks: List[str] = []
        async for token in llm_service.stream_chat(messages):
            assistant_chunks.append(token)
            yield {
                "type": "token",
                "token": token
            }

        full_response = "".join(assistant_chunks).strip()

        # 4. Save assistant turn to DB
        assistant_turn_id = str(uuid.uuid4())
        db_asst_turn = Turn(
            id=assistant_turn_id,
            session_id=session_id,
            user_id=user_id,
            turn_index=turn_index + 1,
            role="assistant",
            content=full_response,
            created_at=datetime.utcnow()
        )
        db.add(db_asst_turn)
        await db.commit()

        # 5. Post-Turn Extraction & Memory Invalidation / Additions
        # Fetch full active-fact contents so the extractor can emit UPDATE (not ADD) on contradiction
        active_contents = [f["content"] for f in await retrieval_service.retrieve_active_facts(
            db=db, query="", user_id=user_id, limit=50,
        )] if user_message and user_message.strip() else []
        extracted_facts = await llm_service.extract_facts(
            user_turn=user_message,
            assistant_turn=full_response,
            reference_date=datetime.utcnow(),
            active_facts=active_contents,
        )

        memory_updated = False
        for ef in extracted_facts:
            if ef.salience_score < settings.SALIENCE_THRESHOLD:
                continue

            try:
                if ef.action in ["UPDATE", "DELETE"] and ef.supersedes_text:
                    await memory_service.manage_memory(
                        db=db,
                        req=MemoryManageRequest(
                            action="replace" if ef.action == "UPDATE" else "remove",
                            target="MEMORY",
                            content=ef.fact if ef.action == "UPDATE" else None,
                            old_text=ef.supersedes_text,
                            category=ef.category,
                            salience_score=ef.salience_score
                        ),
                        user_id=user_id
                    )
                    memory_updated = True
                elif ef.action == "ADD":
                    await memory_service.manage_memory(
                        db=db,
                        req=MemoryManageRequest(
                            action="add",
                            target="MEMORY",
                            content=ef.fact,
                            category=ef.category,
                            salience_score=ef.salience_score
                        ),
                        user_id=user_id
                    )
                    memory_updated = True
            except MemoryCapacityExceededError as e:
                # Log capacity overflow for consolidation
                print(f"[memory persist] capacity exceeded for {e.target}: {e.current_chars}/{e.max_chars} chars")
            except Exception as e:
                print(f"[memory persist] failed ({ef.action} '{ef.fact[:60]}'): {type(e).__name__}: {e}")

        # Final Done Signal
        yield {
            "type": "done",
            "full_response": full_response,
            "extracted_facts": [ef.model_dump() for ef in extracted_facts],
            "memory_updated": memory_updated
        }

companion_agent = CompanionAgent()
