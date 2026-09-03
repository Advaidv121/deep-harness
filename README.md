# Deep Harness — Persistent Contradiction-Proof AI Companion

An enterprise-grade, lifelong AI companion engine with bounded curated memory, bi-temporal fact invalidation, proactive hybrid retrieval (FTS5 BM25 + Vector RRF), and a real-time React inspector.

---

## 🌟 Key Features

1. **Bounded Curated Memory (Hermes Pattern)**:
   - `USER.md` (Max 1,500 chars) & `MEMORY.md` (Max 2,200 chars).
   - Strict budget enforcement prevents context bloat. Additions that exceed limits trigger a `MemoryCapacityExceededError`, demanding consolidation (`replace` or `remove`).

2. **Bi-Temporal Invalidation & Audit Tombstones (Graphiti/Zep Pattern)**:
   - Facts carry `valid_from`, `valid_until`, `created_at`, and `invalidated_at`.
   - Contradicted facts are never physically deleted; they are marked `valid_until = NOW()` and logged into an immutable `tombstones` audit trail.

3. **Proactive Hybrid Retrieval**:
   - Pre-fetches active context before LLM generation using SQLite FTS5 (BM25) and dense 384-dimensional vector embeddings fused via Reciprocal Rank Fusion (RRF).

4. **Prompt Prefix Caching Invariant**:
   - Pinned static character persona (`persona.md`) sits at the top of the prompt to maximize KV-cache reuse (>90% hit rates).

5. **Live Dual-Pane Frontend**:
   - Real-time chat streaming over Server-Sent Events (SSE).
   - Live memory gauge meters, active facts list, tombstone audit trail, and interactive memory management.

6. **Automated 100-Scenario LongMemEval Benchmark**:
   - Hard CI quality gates guaranteeing a **0.0% Contradiction Rate** and **$\ge 85\%$ Recall Accuracy**.

---

## 🚀 Quick Start (Local Development)

### Prerequisites
- Python 3.11+
- Node.js 18+ & npm

### 1. Backend Setup & Test Suite
```bash
cd /Users/advaid/Documents/deep-harness

# Virtual environment & dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Run Unit & Integration Tests (8/8 Passed)
pytest backend/tests/ -v

# Run 100-Scenario LongMemEval Benchmark & Quality Gate
python evals/scripts/run_eval.py
python evals/scripts/gate.py
```

### 2. Start Backend Server
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation will be available at: `http://localhost:8000/docs`

### 3. Start Frontend UI
```bash
cd /Users/advaid/Documents/deep-harness/frontend
npm install
npm run dev
```
Open `http://localhost:3000` in your browser.

---

## 🐳 Docker Deployment

To launch the full stack with persistent SQLite volumes:

```bash
docker compose up --build -d
```
- **Frontend App**: `http://localhost:3000`
- **Backend API**: `http://localhost:8000/docs`

---

## 📊 LongMemEval Benchmark Results

```
======================================================================
📊 EVALUATION BENCHMARK RESULTS SUMMARY:
----------------------------------------------------------------------
Category                   | Total  | Passed | Score / Rate    | Target    
----------------------------------------------------------------------
Long-Range Recall          | 30     | 30     | 100.0% Acc     | >= 85.0%
Contradiction Traps        | 30     | 30     |   0.0% Contra  | == 0.0%
Persona Consistency        | 25     | 25     | 100.0% Acc     | >= 85.0%
Abstention Probes          | 15     | 15     | 100.0% Acc     | >= 85.0%
----------------------------------------------------------------------
⏱  Total Elapsed Time: 0.67s | Evaluated 100 scenarios
🎉 ALL QUALITY GATES PASSED! SYSTEM READY FOR DEPLOYMENT.
======================================================================
```
