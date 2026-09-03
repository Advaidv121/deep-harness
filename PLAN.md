# Deep Harness AI Companion: 18-Hour Milestone Plan

## Phase 1: Core Engine & Bi-Temporal Storage (Hours 0-4)
- [x] Implement SQLite schemas with `aiosqlite` and `SQLAlchemy`.
- [x] Configure SQLite FTS5 virtual table synchronization on insert/update.
- [x] Implement `MemoryService` with bounded character budgets (`USER.md` $\le 1500$, `MEMORY.md` $\le 2200$).
- [x] Implement `MemoryCapacityExceededError` on budget overflow requiring consolidation.
- [x] Implement bi-temporal fact invalidation (`valid_until = NOW()`) and `Tombstone` logging.
- [x] Write pytest unit test suite (`backend/tests/test_memory_service.py`).

## Phase 2: Hybrid Retrieval & Conversational Loop (Hours 4-8)
- [x] Implement 384-dimensional dense vector embeddings and cosine similarity.
- [x] Implement Hybrid Retrieval combining SQLite FTS5 BM25 + Vector Cosine Similarity via RRF ($k=60$).
- [x] Implement `CompanionAgent` with Prompt Prefix Caching invariant (`persona.md` at top).
- [x] Implement 4-way post-turn fact extraction (`ADD | UPDATE | DELETE | NOOP`) with ISO-8601 date anchoring.
- [x] Implement FastAPI REST & Server-Sent Events `/api/v1/chat/stream` endpoints.
- [x] Write integration tests (`backend/tests/test_retrieval.py`, `backend/tests/test_agent_api.py`).

## Phase 3: Frontend Interface & Live Inspector (Hours 8-11)
- [x] Scaffold Vite + React 18 + TypeScript + Tailwind CSS client.
- [x] Implement `useSSE` hook for smooth token streaming and memory event propagation.
- [x] Build Conversational Chat component with quick action testing prompts.
- [x] Build Live Memory & Bi-Temporal Inspector with real-time character budget gauges.
- [x] Build Immutable Audit Trail & Tombstone viewer with strikethrough styling for invalidated facts.
- [x] Build manual Memory Management form with capacity overflow notifications.

## Phase 4: LongMemEval Evaluation Harness (Hours 11-15)
- [x] Generate 100 stratified test scenarios (`evals/data/golden.jsonl`):
  - 30 Long-Range Recall probes
  - 30 Contradiction Traps
  - 25 Persona Consistency probes
  - 15 Abstention Probes (`_abs`)
- [x] Build automated benchmark evaluator (`evals/test_suite.py`, `evals/scripts/run_eval.py`).
- [x] Implement CI hard quality gates (`evals/scripts/gate.py`):
  - **Contradiction Rate**: 0.0% (Verified)
  - **Long-Range Recall**: $\ge 85.0\%$ (Verified: 100.0%)
  - **Persona Consistency**: $\ge 85.0\%$ (Verified: 100.0%)
  - **Abstention Accuracy**: $\ge 85.0\%$ (Verified: 100.0%)

## Phase 5: Containerization & Verification (Hours 15-18)
- [x] Write multi-stage `backend/Dockerfile` and `frontend/Dockerfile` with Nginx reverse proxy.
- [x] Write `docker-compose.yml` for unified 2-service deployment.
- [x] Verify complete full-stack execution locally and in containers.
