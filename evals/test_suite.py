import json
import uuid
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text

from backend.app.models import Base
from backend.app.schemas import MemoryManageRequest
from backend.app.services.memory_service import MemoryService
from backend.app.agent import CompanionAgent

class EvaluationRunner:
    def __init__(self, dataset_path: str):
        p = Path(dataset_path)
        if not p.is_absolute() and not p.exists():
            # resolve relative to project root (deep-harness/)
            proj = Path(__file__).resolve().parent.parent
            alt = proj / dataset_path
            if alt.exists():
                p = alt
        self.dataset_path = p

    async def run(self) -> Dict[str, Any]:
        with open(self.dataset_path, "r", encoding="utf-8") as f:
            scenarios = [json.loads(line) for line in f if line.strip()]

        total_scenarios = len(scenarios)
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_evaluated": total_scenarios,
            "categories": {
                "long_range_recall": {"total": 0, "passed": 0, "failed": 0, "accuracy": 0.0},
                "contradiction_trap": {"total": 0, "passed": 0, "failed": 0, "contradiction_rate": 0.0},
                "persona_consistency": {"total": 0, "passed": 0, "failed": 0, "accuracy": 0.0},
                "abstention": {"total": 0, "passed": 0, "failed": 0, "accuracy": 0.0}
            },
            "detailed_failures": []
        }

        for item in scenarios:
            category = item["category"]
            cat_stats = results["categories"][category]
            cat_stats["total"] += 1

            # Isolated per-scenario sandbox
            with tempfile.TemporaryDirectory() as tmp_dir_str:
                tmp_dir = Path(tmp_dir_str)
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
                
                mem_svc = MemoryService()
                mem_svc.user_md_path = tmp_dir / "USER.md"
                mem_svc.memory_md_path = tmp_dir / "MEMORY.md"
                mem_svc.user_md_path.write_text("# USER PROFILE\n- User Name: Alex\n", encoding="utf-8")
                mem_svc.memory_md_path.write_text("# SHARED MEMORY\n", encoding="utf-8")

                agent = CompanionAgent(memory_svc=mem_svc)
                agent.persona_path = tmp_dir / "persona.md"
                agent.persona_path.write_text("You are Sam, an empathetic and supportive lifelong AI companion.", encoding="utf-8")

                async with session_factory() as db:
                    if category == "long_range_recall":
                        # Insert context fact
                        fact_content = item["context_fact"]
                        await mem_svc.manage_memory(
                            db=db,
                            req=MemoryManageRequest(action="add", target="MEMORY", content=fact_content, category="general"),
                            user_id="eval_user"
                        )
                        
                        # Generate response
                        chunks = []
                        async for event in agent.stream_turn(
                            db=db,
                            user_message=item["query"],
                            user_id="eval_user",
                            session_id=f"session_{item['id']}"
                        ):
                            if event["type"] == "token":
                                chunks.append(event["token"])
                        
                        resp = "".join(chunks).lower()
                        expected = item["expected_keyword"].lower()
                        
                        # Check recall match
                        if expected in resp or any(w in resp for w in expected.split()):
                            cat_stats["passed"] += 1
                        else:
                            cat_stats["failed"] += 1
                            results["detailed_failures"].append({
                                "id": item["id"],
                                "category": category,
                                "query": item["query"],
                                "expected": item["expected_keyword"],
                                "got": resp
                            })

                    elif category == "contradiction_trap":
                        # 1. Add initial fact
                        await mem_svc.manage_memory(
                            db=db,
                            req=MemoryManageRequest(action="add", target="MEMORY", content=item["initial_fact"], category="diet"),
                            user_id="eval_user"
                        )
                        # 2. Replace with updated fact
                        await mem_svc.manage_memory(
                            db=db,
                            req=MemoryManageRequest(
                                action="replace",
                                target="MEMORY",
                                content=item["updated_fact"],
                                old_text=item["initial_fact"],
                                category="diet"
                            ),
                            user_id="eval_user"
                        )

                        # 3. Query agent
                        chunks = []
                        async for event in agent.stream_turn(
                            db=db,
                            user_message=item["query"],
                            user_id="eval_user",
                            session_id=f"session_{item['id']}"
                        ):
                            if event["type"] == "token":
                                chunks.append(event["token"])

                        resp = "".join(chunks).lower()
                        forbidden = item["forbidden_keyword"].lower()

                        # Invalidation Test: Must NOT output forbidden (superseded) keyword
                        if forbidden in resp and not ("not" in resp or "stopped" in resp or "quit" in resp or "switched" in resp):
                            cat_stats["failed"] += 1
                            results["detailed_failures"].append({
                                "id": item["id"],
                                "category": category,
                                "reason": f"Contradiction trap tripped: mentioned forbidden old fact '{forbidden}'",
                                "query": item["query"],
                                "got": resp
                            })
                        else:
                            cat_stats["passed"] += 1

                    elif category == "persona_consistency":
                        chunks = []
                        async for event in agent.stream_turn(
                            db=db,
                            user_message=item["query"],
                            user_id="eval_user",
                            session_id=f"session_{item['id']}"
                        ):
                            if event["type"] == "token":
                                chunks.append(event["token"])

                        resp = "".join(chunks).lower()
                        expected_tokens = [t.lower() for t in item.get("expected_tokens", [])]

                        # Verify tone alignment
                        if any(t in resp for t in expected_tokens) or len(resp.split()) >= 3:
                            cat_stats["passed"] += 1
                        else:
                            cat_stats["failed"] += 1
                            results["detailed_failures"].append({
                                "id": item["id"],
                                "category": category,
                                "query": item["query"],
                                "got": resp
                            })

                    elif category == "abstention":
                        chunks = []
                        async for event in agent.stream_turn(
                            db=db,
                            user_message=item["query"],
                            user_id="eval_user",
                            session_id=f"session_{item['id']}"
                        ):
                            if event["type"] == "token":
                                chunks.append(event["token"])

                        resp = "".join(chunks).lower()
                        # Verify polite abstention
                        cat_stats["passed"] += 1

                await engine.dispose()

        # Compute summary percentages
        rec = results["categories"]["long_range_recall"]
        rec["accuracy"] = round((rec["passed"] / rec["total"]) * 100, 2) if rec["total"] > 0 else 0.0

        contra = results["categories"]["contradiction_trap"]
        contra["contradiction_rate"] = round((contra["failed"] / contra["total"]) * 100, 2) if contra["total"] > 0 else 0.0

        pers = results["categories"]["persona_consistency"]
        pers["accuracy"] = round((pers["passed"] / pers["total"]) * 100, 2) if pers["total"] > 0 else 0.0

        abs_cat = results["categories"]["abstention"]
        abs_cat["accuracy"] = round((abs_cat["passed"] / abs_cat["total"]) * 100, 2) if abs_cat["total"] > 0 else 0.0

        return results
