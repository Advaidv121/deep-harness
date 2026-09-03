# Deep Harness AI Companion: Architecture Specification

## 1. System Overview

The **Deep Harness AI Companion** is a persistent, contradiction-proof conversational intelligence engine designed to maintain lifelong relationships without context bloat, hallucination, or contradiction regression.

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                COMPANION ARCHITECTURE                                   │
│                                                                                         │
│  [STATIC PREFIX - CACHED]                                                               │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐  │
│  │ 1. Core Instructions + Tool Schemas                                               │  │
│  │ 2. Pinned Companion Persona (persona.md / AGENTS.md ~2,000 chars) [Cache Breakpoint] │  │
│  └───────────────────────────────────────────────────────────────────────────────────┘  │
│                                           │                                             │
│  [DYNAMIC SUFFIX - PER TURN]              ▼                                             │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐  │
│  │ 3. Curated Bounded Snapshot: USER.md (1,500 chars) + MEMORY.md (2,200 chars)       │  │
│  │ 4. Proactive Retrieval: Top-K Bi-temporal Facts (FTS5 BM25 + MiniLM 384d via RRF)  │  │
│  │ 5. Multi-Turn Session Buffer (Windowed turns)                                     │  │
│  └───────────────────────────────────────────────────────────────────────────────────┘  │
│                                           │                                             │
│                                           ▼                                             │
│                                 [ LLM Generation (SSE) ]                                │
│                                           │                                             │
│                                           ▼                                             │
│  [POST-TURN ASYNC EXTRACTION]                                                           │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐  │
│  │ • 4-Way Salience Gating: ADD (score ≥ 0.7), UPDATE, DELETE, NOOP                  │  │
│  │ • Relative Date Anchoring (e.g. "next Tuesday" ➔ ISO-8601 calendar date)           │  │
│  │ • Bi-Temporal Invalidation (Sets valid_until = NOW(), creates audit Tombstone)     │  │
│  │ • Forced Consolidation if USER.md / MEMORY.md exceeds character budget            │  │
│  └───────────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Architectural Invariants

### Invariant 1: Bounded Curated Markdown Memory (Hermes Pattern)
- `USER.md` profile snapshot strictly capped at **1,500 characters**.
- `MEMORY.md` shared relationship notes strictly capped at **2,200 characters**.
- If an addition breaches capacity, `manage_memory` raises `MemoryCapacityExceededError`, demanding consolidation (`replace` or `remove`).

### Invariant 2: Bi-Temporal Invalidation & Audit Tombstones (Graphiti/Zep Pattern)
Every fact record in SQLite carries four core timestamps:
- `valid_from`: When the fact became true in the real world.
- `valid_until`: `NULL` if actively true; timestamp when superseded by a new fact.
- `created_at`: When the record was inserted into the database.
- `invalidated_at`: When a contradiction or removal invalidated the fact.
- `tombstones` table preserves an immutable audit trail with `fact_id`, `reason` (`contradicted`, `decayed`, `manual_removal`), and `superseded_by`.

### Invariant 3: Proactive Hybrid Pre-Fetching
Reactive tool-calling suffers a 30–45% trigger failure rate on casual banter. Deep Harness pre-fetches active context prior to LLM generation using:
- **Lexical BM25 Search**: SQLite FTS5 index on active facts.
- **Dense Vector Cosine Similarity**: Normalized 384-dimensional embeddings.
- **Reciprocal Rank Fusion (RRF)**:
  $$RRF(d) = \frac{1}{60 + \text{rank}_{\text{BM25}}(d)} + \frac{1}{60 + \text{rank}_{\text{Dense}}(d)}$$

### Invariant 4: Prompt Prefix Caching
The system prompt places byte-stable persona instructions at the absolute top of the prompt prefix. Dynamic context (memory snapshots, retrieved facts, turns) is appended afterwards, maximizing KV-cache reuse (>90% hit rate) across consecutive turns.

### Invariant 5: 4-Way Salience Gating & Relative Date Normalization
Post-turn extraction classifies turn insights into `ADD`, `UPDATE`, `DELETE`, or `NOOP`. Facts below salience $\ge 0.70$ are dropped. Relative temporal markers (*"yesterday"*, *"next week"*) are normalized to absolute ISO-8601 calendar dates.
