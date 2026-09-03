import re
from typing import List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from backend.app.config import get_settings
from backend.app.models import Fact
from backend.app.services.embedding_service import embedding_service

settings = get_settings()

def sanitize_fts_query(query: str) -> str:
    clean_terms = re.findall(r'\b[A-Za-z0-9_]+\b', query)
    if not clean_terms:
        return ""
    return " | ".join(clean_terms)  # postgres tsquery OR

class RetrievalService:
    def __init__(self, rrf_k: int = 60, top_k: int = 5):
        self.rrf_k = rrf_k
        self.top_k = top_k

    def _qdrant(self):
        try:
            from backend.app.services.qdrant_service import qdrant_service
            return qdrant_service
        except Exception:
            return None

    async def retrieve_active_facts(self, db: AsyncSession, query: str, user_id: str = "default_user", limit: int = 5) -> List[Dict[str, Any]]:
        """
        Hybrid: Qdrant (dense+ sparse) filtered by user_id+valid_until, fallback to Postgres tsvector + dense RRF.
        Always filters valid_until IS NULL.
        """
        if not query or not query.strip():
            stmt = select(Fact).where(Fact.user_id == user_id, Fact.valid_until.is_(None)).order_by(Fact.created_at.desc()).limit(limit)
            result = await db.execute(stmt)
            facts = result.scalars().all()
            return [{"id": f.id, "content": f.content, "category": f.category, "rrf_score": 1.0} for f in facts]

        # 1. Fetch active facts map (needed for fallback and for enriching Qdrant hits)
        stmt = select(Fact).where(Fact.user_id == user_id, Fact.valid_until.is_(None))
        result = await db.execute(stmt)
        active_facts = result.scalars().all()
        if not active_facts:
            return []
        active_fact_map = {f.id: f for f in active_facts}
        active_ids = set(active_fact_map.keys())

        # 2. Try Qdrant hybrid first
        qs = self._qdrant()
        qdrant_ranks: Dict[str, int] = {}
        qdrant_hits = []
        if qs is not None:
            try:
                qdrant_hits = qs.hybrid_search(query, user_id, limit=limit*2)
                for rank, hit in enumerate(qdrant_hits, 1):
                    fid = hit["id"]
                    if fid in active_ids:
                        qdrant_ranks[fid] = rank
            except Exception:
                qdrant_ranks = {}

        # 3. Postgres tsvector lexical ranking (fallback / complement)
        # Use tsvector if available, else ILIKE fallback
        pg_ranks: Dict[str, int] = {}
        try:
            # build tsquery safely
            terms = re.findall(r'\b[A-Za-z0-9]+\b', query.lower())
            tsq = " | ".join(terms) if terms else ""
            if tsq:
                sql = text("""
                    SELECT id FROM facts
                    WHERE user_id = :uid AND valid_until IS NULL
                      AND content_tsv @@ to_tsquery('english', :q)
                    ORDER BY ts_rank(content_tsv, to_tsquery('english', :q)) DESC
                    LIMIT 20
                """)
                res = await db.execute(sql, {"uid": user_id, "q": tsq})
                for idx, row in enumerate(res.fetchall(), 1):
                    fid = row[0]
                    if fid in active_ids and fid not in pg_ranks:
                        pg_ranks[fid] = idx
        except Exception:
            pass
        # fallback token overlap if pg produced nothing
        lexical_ranks = qdrant_ranks if qdrant_ranks else pg_ranks
        if not lexical_ranks:
            query_tokens = set(query.lower().split())
            scored = []
            for f in active_facts:
                overlap = len(query_tokens.intersection(set(f.content.lower().split())))
                if overlap > 0:
                    scored.append((f.id, overlap))
            scored.sort(key=lambda x: x[1], reverse=True)
            for idx, (fid, _) in enumerate(scored, 1):
                lexical_ranks[fid] = idx

        # 4. Dense vector rank (local) — always computed for RRF fusion
        query_vec = embedding_service.encode(query)
        vector_scores: List[Tuple[str, float]] = []
        for f in active_facts:
            if f.embedding:
                fact_vec = embedding_service.from_bytes(f.embedding)
                if fact_vec.shape[0] != query_vec.shape[0]:
                    fact_vec = embedding_service.encode(f.content)
            else:
                fact_vec = embedding_service.encode(f.content)
            if fact_vec.shape[0] != query_vec.shape[0]:
                sim = 0.0
            else:
                sim = embedding_service.cosine_similarity(query_vec, fact_vec)
            vector_scores.append((f.id, sim))
        vector_scores.sort(key=lambda x: x[1], reverse=True)
        dense_ranks: Dict[str, int] = {fid: rank for rank, (fid, _) in enumerate(vector_scores, 1)}

        # 5. RRF fusion of lexical (Qdrant or Postgres) + dense
        rrf_scores: Dict[str, float] = {}
        candidates = set(lexical_ranks.keys()).union(set(dense_ranks.keys()))
        for fid in candidates:
            s = 0.0
            if fid in lexical_ranks:
                s += 1.0 / (self.rrf_k + lexical_ranks[fid])
            if fid in dense_ranks:
                s += 1.0 / (self.rrf_k + dense_ranks[fid])
            rrf_scores[fid] = s
        sorted_candidates = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:limit]
        out = []
        for fid, score in sorted_candidates:
            fact = active_fact_map.get(fid)
            if fact:
                out.append({"id": fact.id, "content": fact.content, "category": fact.category, "salience_score": fact.salience_score, "rrf_score": score, "created_at": fact.created_at.isoformat() if fact.created_at else None})
        return out

retrieval_service = RetrievalService()
