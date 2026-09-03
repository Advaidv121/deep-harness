import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from backend.app.config import get_settings
from backend.app.models import Fact, Tombstone
from backend.app.schemas import MemoryManageRequest, MemoryOperationResponse, FactResponse, TombstoneResponse
from backend.app.services.embedding_service import embedding_service

settings = get_settings()

class MemoryCapacityExceededError(Exception):
    def __init__(self, target: str, current_chars: int, attempted_chars: int, max_chars: int, current_content: str):
        self.target = target
        self.current_chars = current_chars
        self.attempted_chars = attempted_chars
        self.max_chars = max_chars
        self.current_content = current_content
        super().__init__(
            f"Memory budget exceeded for {target}.md ({attempted_chars}/{max_chars} chars). "
            f"Consolidation required: use 'replace' or 'remove' to free space."
        )

class MemoryService:
    def __init__(self):
        self.user_md_path: Path = settings.MEMORY_DIR / "USER.md"
        self.memory_md_path: Path = settings.MEMORY_DIR / "MEMORY.md"
        self._ensure_files()

    def _ensure_files(self):
        settings.MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        if not self.user_md_path.exists():
            self.user_md_path.write_text("# USER PROFILE\n", encoding="utf-8")
        if not self.memory_md_path.exists():
            self.memory_md_path.write_text("# SHARED MEMORY & CONTEXT\n", encoding="utf-8")

    def get_user_display_name(self, user_id: str) -> str:
        if user_id in ["alex_prod", "default_user"]:
            return "Alex"
        if user_id == "clara_orbital":
            return "Clara"
        if user_id == "maya_architect":
            return "Maya"
        if user_id.startswith("user_"):
            parts = user_id.split("_")
            if len(parts) >= 2 and parts[1]:
                return parts[1].capitalize()
        return user_id.capitalize()

    def _get_user_path(self, target: str, user_id: str = "default_user") -> Path:
        target_upper = target.upper()
        if user_id in ["alex_prod", "default_user"]:
            return self.user_md_path if target_upper == "USER" else self.memory_md_path
        suffix = f"_{user_id}.md"
        return settings.MEMORY_DIR / (f"USER{suffix}" if target_upper == "USER" else f"MEMORY{suffix}")

    def read_markdown(self, target: str, user_id: str = "default_user") -> str:
        path = self._get_user_path(target, user_id)
        if not path.exists():
            name = self.get_user_display_name(user_id)
            if target.upper() == "USER":
                return f"# USER PROFILE\n- User Name: {name}\n- User ID: {user_id}\n"
            return f"# SHARED MEMORY & CONTEXT\n"
        return path.read_text(encoding="utf-8")

    def write_markdown(self, target: str, content: str, user_id: str = "default_user"):
        path = self._get_user_path(target, user_id)
        path.write_text(content, encoding="utf-8")

    def get_limits(self, target: str) -> int:
        return settings.USER_MD_MAX_CHARS if target.upper() == "USER" else settings.MEMORY_MD_MAX_CHARS

    def get_snapshot(self, user_id: str = "default_user") -> Dict[str, Any]:
        user_content = self.read_markdown("USER", user_id=user_id)
        memory_content = self.read_markdown("MEMORY", user_id=user_id)
        return {
            "user_md": user_content,
            "memory_md": memory_content,
            "user_md_chars": len(user_content),
            "user_md_max": settings.USER_MD_MAX_CHARS,
            "memory_md_chars": len(memory_content),
            "memory_md_max": settings.MEMORY_MD_MAX_CHARS,
        }

    def _qdrant(self):
        try:
            from backend.app.services.qdrant_service import qdrant_service
            return qdrant_service
        except Exception:
            return None

    async def manage_memory(
        self,
        db: AsyncSession,
        req: MemoryManageRequest,
        user_id: str = "default_user"
    ) -> MemoryOperationResponse:
        target_upper = req.target.upper()
        current_text = self.read_markdown(target_upper, user_id=user_id)
        max_chars = self.get_limits(target_upper)
        now = datetime.utcnow()
        qs = self._qdrant()

        if req.action == "add":
            if not req.content or not req.content.strip():
                raise ValueError("Content cannot be empty for 'add' operation.")
            entry = f"- {req.content.strip()}"
            new_text = current_text.rstrip() + "\n" + entry + "\n"
            if len(new_text) > max_chars:
                raise MemoryCapacityExceededError(
                    target=target_upper,
                    current_chars=len(current_text),
                    attempted_chars=len(new_text),
                    max_chars=max_chars,
                    current_content=current_text
                )
            self.write_markdown(target_upper, new_text, user_id=user_id)
            fact_id = str(uuid.uuid4())
            vec = embedding_service.encode(req.content)
            fact = Fact(
                id=fact_id,
                user_id=user_id,
                category=req.category or "other",
                content=req.content.strip(),
                salience_score=req.salience_score or 1.0,
                valid_from=now,
                valid_until=None,
                created_at=now,
                invalidated_at=None,
                linked_to=None,
                embedding=embedding_service.to_bytes(vec)
            )
            db.add(fact)
            await db.flush()
            # keep tsvector in sync (postgres)
            try:
                await db.execute(text("UPDATE facts SET content_tsv = to_tsvector('english', :c) WHERE id = :id"), {"c": req.content.strip(), "id": fact_id})
            except Exception:
                pass
            await db.commit()
            # dual-write Qdrant (best-effort)
            if qs:
                try:
                    qs.upsert_fact(fact_id, req.content.strip(), req.category or "other", user_id, None)
                except Exception:
                    pass
            return MemoryOperationResponse(success=True, message=f"Added fact to {target_upper}.md and bi-temporal database.", target=target_upper, chars_used=len(new_text), char_limit=max_chars)

        elif req.action == "replace":
            if not req.old_text:
                raise ValueError("'old_text' is required for 'replace' operation.")
            if not req.content:
                raise ValueError("'content' is required for 'replace' operation.")
            if req.old_text not in current_text:
                found = False
                for line in current_text.splitlines():
                    if req.old_text.lower() in line.lower():
                        current_text = current_text.replace(line, f"- {req.content.strip()}")
                        found = True
                        break
                if not found:
                    raise ValueError(f"Substring '{req.old_text}' not found in {target_upper}.md.")
            else:
                new_entry = f"- {req.content.strip()}" if not req.content.startswith("-") else req.content.strip()
                current_text = current_text.replace(req.old_text, new_entry)
            if len(current_text) > max_chars:
                raise MemoryCapacityExceededError(target=target_upper, current_chars=len(self.read_markdown(target_upper)), attempted_chars=len(current_text), max_chars=max_chars, current_content=current_text)
            self.write_markdown(target_upper, current_text)
            new_fact_id = str(uuid.uuid4())
            vec = embedding_service.encode(req.content)
            stmt = select(Fact).where(Fact.user_id == user_id, Fact.valid_until.is_(None))
            result = await db.execute(stmt)
            active_facts = result.scalars().all()
            superseded_id = None
            for old_f in active_facts:
                if req.old_text.lower() in old_f.content.lower() or old_f.content.lower() in req.old_text.lower():
                    old_f.valid_until = now
                    old_f.invalidated_at = now
                    superseded_id = old_f.id
                    tombstone = Tombstone(id=str(uuid.uuid4()), fact_id=old_f.id, user_id=user_id, reason="contradicted", superseded_by=new_fact_id, created_at=now)
                    db.add(tombstone)
                    # Qdrant delete invalidated vector
                    if qs:
                        try:
                            qs.delete_fact(old_f.id)
                        except Exception:
                            pass
            new_fact = Fact(id=new_fact_id, user_id=user_id, category=req.category or "other", content=req.content.strip(), salience_score=req.salience_score or 1.0, valid_from=now, valid_until=None, created_at=now, invalidated_at=None, linked_to=superseded_id, embedding=embedding_service.to_bytes(vec))
            db.add(new_fact)
            await db.flush()
            try:
                await db.execute(text("UPDATE facts SET content_tsv = to_tsvector('english', :c) WHERE id = :id"), {"c": req.content.strip(), "id": new_fact_id})
            except Exception:
                pass
            await db.commit()
            if qs:
                try:
                    qs.upsert_fact(new_fact_id, req.content.strip(), req.category or "other", user_id, None)
                except Exception:
                    pass
            return MemoryOperationResponse(success=True, message=f"Replaced fact in {target_upper}.md and invalidated prior bi-temporal record.", target=target_upper, chars_used=len(current_text), char_limit=max_chars)

        elif req.action == "remove":
            if not req.old_text:
                raise ValueError("'old_text' is required for 'remove' operation.")
            found = False
            lines = current_text.splitlines()
            new_lines = []
            for line in lines:
                if req.old_text.lower() in line.lower():
                    found = True
                    continue
                new_lines.append(line)
            if not found:
                raise ValueError(f"Target text '{req.old_text}' not found in {target_upper}.md.")
            new_text = "\n".join(new_lines) + "\n"
            self.write_markdown(target_upper, new_text)
            stmt = select(Fact).where(Fact.user_id == user_id, Fact.valid_until.is_(None))
            result = await db.execute(stmt)
            active_facts = result.scalars().all()
            for old_f in active_facts:
                if req.old_text.lower() in old_f.content.lower() or old_f.content.lower() in req.old_text.lower():
                    old_f.valid_until = now
                    old_f.invalidated_at = now
                    tombstone = Tombstone(id=str(uuid.uuid4()), fact_id=old_f.id, user_id=user_id, reason="manual_removal", superseded_by=None, created_at=now)
                    db.add(tombstone)
                    if qs:
                        try:
                            qs.delete_fact(old_f.id)
                        except Exception:
                            pass
            await db.commit()
            return MemoryOperationResponse(success=True, message=f"Removed fact from {target_upper}.md and created tombstone.", target=target_upper, chars_used=len(new_text), char_limit=max_chars)

        raise ValueError(f"Unknown action: {req.action}")

    async def list_facts(self, db: AsyncSession, user_id: str = "default_user", active_only: bool = False) -> List[FactResponse]:
        stmt = select(Fact).where(Fact.user_id == user_id)
        if active_only:
            stmt = stmt.where(Fact.valid_until.is_(None))
        stmt = stmt.order_by(Fact.created_at.desc())
        result = await db.execute(stmt)
        facts = result.scalars().all()
        return [FactResponse(id=f.id, user_id=f.user_id, category=f.category, content=f.content, salience_score=f.salience_score, valid_from=f.valid_from, valid_until=f.valid_until, created_at=f.created_at, invalidated_at=f.invalidated_at, linked_to=f.linked_to, is_active=f.valid_until is None) for f in facts]

    async def list_tombstones(self, db: AsyncSession, user_id: str = "default_user") -> List[TombstoneResponse]:
        stmt = select(Tombstone).where(Tombstone.user_id == user_id).order_by(Tombstone.created_at.desc())
        result = await db.execute(stmt)
        tombstones = result.scalars().all()
        return [TombstoneResponse(id=t.id, fact_id=t.fact_id, user_id=t.user_id, reason=t.reason, superseded_by=t.superseded_by, created_at=t.created_at) for t in tombstones]

memory_service = MemoryService()
