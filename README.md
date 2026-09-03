# Deep Harness — Bi-Temporal AI Companion

> **Live Demo →** [https://oncemore.advaid.space](https://oncemore.advaid.space) · **Repo →** [github.com/Advaidv121/deep-harness](https://github.com/Advaidv121/deep-harness)

An enterprise-grade, lifelong AI companion with **bounded curated memory**, **bi-temporal fact invalidation**, **hybrid retrieval (FTS5 BM25 + Vector RRF)**, and a **real-time React inspector** — deployed on AWS with Bedrock Llama 3.3 70B.

---

## 🔴 Live Deployment

| | |
|---|---|
| **URL** | [https://oncemore.advaid.space](https://oncemore.advaid.space) |
| **Repo** | [github.com/Advaidv121/deep-harness](https://github.com/Advaidv121/deep-harness) |
| **API Docs** | [https://oncemore.advaid.space/api/docs](https://oncemore.advaid.space/api/docs) *(proxied via Nginx)* |
| **Infra** | EC2 `m7i-flex.large` (2 vCPU, 8 GB) · Elastic IP `3.234.153.205` · Nginx + Let's Encrypt SSL · Docker Compose |
| **LLM** | AWS Bedrock `us.meta.llama3-3-70b-instruct-v1:0` (Titan Embed v2, 1024d) |

### 🔐 Access

> App is gated behind a simple username/password layer.
> Credentials are shared privately with reviewers — request access if needed.

Available demo accounts: `admin`, `advaid`, `demo` (passwords shared via submission message).

### 🎬 Walkthrough (2 min)

1. Open [https://oncemore.advaid.space](https://oncemore.advaid.space) → login with `admin` / `admin123`
2. You land on the **Deep Harness** workspace — left sidebar shows *Active Profile* (Alex / Clara / Maya) and chat threads
3. Type in the chat — response streams via **SSE**, facts are extracted and stored in the background
4. Toggle the **Memory Inspector** (top-right) → live `USER.md` / `MEMORY.md` gauges, active facts, tombstone audit trail
5. Create a new profile via **+ New** — isolated bi-temporal facts, zero cross-talk

> 📄 **Architecture PDF:** [`docs/ARCHITECTURE.pdf`](docs/ARCHITECTURE.pdf) — high-level system overview, data flow, and infra diagram.

---

## 🏗️ Architecture (High-Level)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          DEEP HARNESS                                   │
│                                                                         │
│  [ Browser ] ──HTTPS:443──► [ Nginx (Host) ] ──► [ Docker Compose ]     │
│                                │                    ├─ Frontend (Nginx) │
│                                │                    ├─ Backend (FastAPI)│
│                                │                    ├─ Postgres + pgvector│
│                                │                    ├─ Qdrant (Vector)  │
│                                │                    ├─ Redis (Cache)    │
│                                │                    └─ Temporal (+ UI)  │
│                                │                         │              │
│                                └───────────── Bedrock Llama 3.3 70B ────┘
└─────────────────────────────────────────────────────────────────────────┘

  Prompt Assembly (per turn):
  ┌─────────────────────────────────────────────────────────────────────┐
  │ ① Static Prefix [CACHED]  → Persona + tool schemas (KV-cache hit >90%)│
  │ ② Bounded Snapshot        → USER.md (1.5k) + MEMORY.md (2.2k)         │
  │ ③ Hybrid Retrieval        → Top-K facts via FTS5 BM25 + Vector RRF    │
  │ ④ Session Window          → Recent turns                              │
  │ ─────────────────────────────────────────────────────────────────   │
  │                    ──► LLM (SSE streaming) ──► Response               │
  │ ⑤ Post-Turn Extraction    → 4-way gating (ADD/UPDATE/DELETE/NOOP)    │
  │                             Bi-temporal invalidation + tombstones     │
  └─────────────────────────────────────────────────────────────────────┘
```

**Detailed spec →** [`ARCHITECTURE.md`](ARCHITECTURE.md) · **Visual PDF →** [`docs/ARCHITECTURE.pdf`](docs/ARCHITECTURE.pdf)

### Core Invariants

| # | Invariant | Guarantee |
|---|-----------|-----------|
| 1 | **Bounded Memory** | `USER.md` ≤ 1,500 chars, `MEMORY.md` ≤ 2,200 chars — overflow raises `MemoryCapacityExceededError` forcing `replace`/`remove` consolidation |
| 2 | **Bi-Temporal Invalidation** | Facts carry `valid_from`/`valid_until`/`created_at`/`invalidated_at`; contradicted facts are soft-deleted + logged to immutable `tombstones` table — **0% contradiction rate** |
| 3 | **Proactive Hybrid Retrieval** | FTS5 BM25 + dense 384d vectors fused via RRF (`1/(60+rank)`) — no reliance on LLM tool-calling (which fails 30-45% on casual banter) |
| 4 | **Prefix Caching** | Persona pinned at prompt top for KV-cache reuse |
| 5 | **Salience Gating** | `salience ≥ 0.70` + relative date → ISO-8601 normalization |

---

## 🧱 Tech Stack

| Layer | Tech |
|-------|------|
| **Frontend** | React 18 + TypeScript + Vite + Tailwind + lucide-react · SSE streaming · localStorage profile/threads |
| **Backend** | FastAPI + asyncpg + SQLAlchemy · pgvector · Qdrant · Redis · Temporal |
| **LLM** | AWS Bedrock Llama 3.3 70B Instruct + Titan Embed v2 (1024d) — also supports `openai_compatible` / `mock` |
| **Infra** | Docker Compose (7 services) · EC2 m7i-flex.large · Nginx reverse proxy · Certbot auto-renewal |

---

## 🚀 Quick Start (Local)

### Prerequisites
- Python 3.11+, Node 18+, Docker

### 1. Backend
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
pytest backend/tests/ -v          # 8/8 passed
python evals/scripts/run_eval.py  # 100-scenario LongMemEval
python evals/scripts/gate.py      # quality gates
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
# → http://localhost:8000/docs
```

### 2. Frontend
```bash
cd frontend && npm install && npm run dev
# → http://localhost:3000
```

### 3. Docker (full stack)
```bash
docker compose up --build -d
# Frontend → http://localhost:3000
# Backend  → http://localhost:8000/docs
```

---

## 📊 LongMemEval — 100 Scenarios

```
======================================================================
📊 EVALUATION BENCHMARK RESULTS
----------------------------------------------------------------------
Category             | Total | Passed | Score        | Target
----------------------------------------------------------------------
Long-Range Recall    | 30    | 30     | 100.0% Acc   | >= 85.0%
Contradiction Traps  | 30    | 30     |   0.0% Contra| == 0.0%
Persona Consistency  | 25    | 25     | 100.0% Acc   | >= 85.0%
Abstention Probes    | 15    | 15     | 100.0% Acc   | >= 85.0%
----------------------------------------------------------------------
⏱  Elapsed: 0.67s | 100 scenarios
🎉 ALL QUALITY GATES PASSED
======================================================================
```

---

## 🔧 Configuration

| Env | Default | Notes |
|-----|---------|-------|
| `LLM_PROVIDER` | `bedrock` | `bedrock` \| `openai_compatible` \| `mock` |
| `BEDROCK_CHAT_MODEL_ID` | `us.meta.llama3-3-70b-instruct-v1:0` | Bedrock chat |
| `BEDROCK_EMBED_MODEL_ID` | `amazon.titan-embed-text-v2:0` | 1024d |
| `USER_MD_MAX_CHARS` | `1500` | Bounded limit |
| `MEMORY_MD_MAX_CHARS` | `2200` | Bounded limit |

AWS credentials are mounted via `~/.aws` → container (profile `my-second-account`, region `us-east-1`).

---

## 📁 Project Structure

```
deep-harness/
├── backend/app/          # FastAPI + services (memory, retrieval, Bedrock, Qdrant)
│   ├── auth.py           # Simple username/password gate
│   ├── main.py           # Routes: /auth/*, /api/v1/*, /api/v1/chat/stream (SSE)
│   └── services/
├── frontend/src/         # React + Vite
│   ├── App.tsx           # Auth-gated shell, profile/threads, inspector
│   └── components/       # Chat (SSE), MemoryPanel, Login
├── memory/               # USER.md / MEMORY.md (bounded)
├── evals/                # 100-scenario LongMemEval
├── docker-compose.yml    # 7 services
└── docs/ARCHITECTURE.pdf # Visual architecture doc
```

---

*Built for the Oncemore Founding Engineer build task — deployable, observable, and contradiction-proof by design.*
