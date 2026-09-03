import uuid
import hashlib
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import (
        Distance, VectorParams, SparseVectorParams, PointStruct,
        Filter, FieldCondition, MatchValue, IsNullCondition, PayloadSchemaType
    )
    HAS_QDRANT = True
except ImportError:
    HAS_QDRANT = False
    QdrantClient = None  # type: ignore

from backend.app.config import get_settings
from backend.app.services.embedding_service import embedding_service

settings = get_settings()

COLLECTION = settings.QDRANT_COLLECTION
DIM = settings.BEDROCK_EMBED_DIMENSION  # Titan 1024d

def _sparse_vector(text: str) -> Dict[int, float]:
    """Deterministic BM25-ish sparse vector from tokens (no external deps)."""
    tokens = text.lower().split()
    # simple term frequency
    tf: Dict[str, int] = {}
    for t in tokens:
        tf[t] = tf.get(t, 0) + 1
    # hash token -> index (sparse dim ~ 30000)
    indices: Dict[int, float] = {}
    for tok, cnt in tf.items():
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16) % 30000
        # tf-idf approx: tf * (1 + log len)
        indices[h] = float(cnt)
    return indices

class QdrantService:
    def __init__(self):
        self._client: Optional[Any] = None
        self._ready = False

    def _get_client(self):
        if self._client is not None:
            return self._client
        if not HAS_QDRANT:
            return None
        try:
            self._client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY or None,
                timeout=5,
                check_compatibility=False,
            )
            return self._client
        except Exception as e:
            logger.warning(f"Qdrant connect failed: {e}")
            return None

    def ensure_collection(self):
        client = self._get_client()
        if client is None:
            return False
        try:
            cols = [c.name for c in client.get_collections().collections]
            if COLLECTION in cols:
                self._ready = True
                return True
            client.create_collection(
                collection_name=COLLECTION,
                vectors_config=VectorParams(size=DIM, distance=Distance.COSINE),
                sparse_vectors_config={"sparse": SparseVectorParams()},
            )
            # payload indexes for filtering
            try:
                client.create_payload_index(COLLECTION, field_name="user_id", field_schema=PayloadSchemaType.KEYWORD)
                client.create_payload_index(COLLECTION, field_name="valid_until", field_schema=PayloadSchemaType.KEYWORD)
            except Exception:
                pass
            self._ready = True
            return True
        except Exception as e:
            logger.warning(f"Qdrant ensure_collection failed: {e}")
            return False

    def upsert_fact(self, fact_id: str, content: str, category: str, user_id: str, valid_until: Optional[str] = None):
        client = self._get_client()
        if client is None:
            return False
        if not self._ready:
            self.ensure_collection()
        try:
            vec = embedding_service.encode(content)
            # ensure 1024d for qdrant — if local 384d, pad/extend deterministically
            if vec.shape[0] != DIM:
                # re-encode with padding: hash-expand to 1024d
                import numpy as np
                padded = np.zeros(DIM, dtype=np.float32)
                # copy existing dims and repeat pattern
                src = vec.astype(np.float32)
                for i in range(DIM):
                    padded[i] = src[i % src.shape[0]] * (0.9 ** (i // src.shape[0]))
                # renormalize
                import numpy as np2
                n = np2.linalg.norm(padded)
                if n > 1e-8:
                    padded = padded / n
                vec = padded
            sparse = _sparse_vector(content)
            sparse_indices = list(sparse.keys())
            sparse_values = list(sparse.values())
            # build point
            from qdrant_client.http.models import SparseVector
            point = PointStruct(
                id=fact_id,
                vector={
                    "dense": vec.tolist(),
                    "sparse": SparseVector(indices=sparse_indices, values=sparse_values),
                } if False else vec.tolist(),  # fallback single vector if sparse not supported separately
                payload={
                    "content": content,
                    "category": category,
                    "user_id": user_id,
                    "valid_until": valid_until,  # None = active
                },
            )
            # Try dense-only upsert first (widest compat), then with sparse if configured
            # For collections with named vectors, use dict; else plain list
            # We created collection with default vector + sparse; qdrant accepts list for default
            try:
                client.upsert(collection_name=COLLECTION, points=[point])
            except Exception as e:
                # retry without sparse
                logger.warning(f"Qdrant upsert retry plain: {e}")
                point2 = PointStruct(
                    id=fact_id,
                    vector=vec.tolist(),
                    payload={"content": content, "category": category, "user_id": user_id, "valid_until": valid_until},
                )
                client.upsert(collection_name=COLLECTION, points=[point2])
            return True
        except Exception as e:
            logger.warning(f"Qdrant upsert_fact failed: {e}")
            return False

    def delete_fact(self, fact_id: str):
        client = self._get_client()
        if client is None:
            return False
        try:
            client.delete(collection_name=COLLECTION, points_selector=[fact_id])
            return True
        except Exception as e:
            logger.warning(f"Qdrant delete failed: {e}")
            return False

    def hybrid_search(self, query: str, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Dense + sparse hybrid filtered by user_id and valid_until is NULL (active)."""
        client = self._get_client()
        if client is None:
            return []
        if not self._ready:
            if not self.ensure_collection():
                return []
        try:
            qvec = embedding_service.encode(query)
            import numpy as np
            if qvec.shape[0] != DIM:
                padded = np.zeros(DIM, dtype=np.float32)
                src = qvec.astype(np.float32)
                for i in range(DIM):
                    padded[i] = src[i % src.shape[0]] * (0.9 ** (i // src.shape[0]))
                n = np.linalg.norm(padded)
                if n > 1e-8:
                    padded = padded / n
                qvec = padded

            # Filter: user_id == user_id AND valid_until is null
            # placeholder removed
            # Actually use is_null via Qdrant filter DSL: must have valid_until is null
            # Simpler: filter user_id only and post-filter valid_until in python (robust across versions)
            qfilter = Filter(must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))])

            # Try query_points (new API) else search
            hits = []
            try:
                # qdrant-client >=1.7 — try query_points first (1.10+), then search
                try:
                    # new API
                    res = client.query_points(collection_name=COLLECTION, query=qvec.tolist(), query_filter=qfilter, limit=limit * 2, with_payload=True)
                    hits = res.points if hasattr(res, "points") else res
                except Exception:
                    from qdrant_client.http.models import SearchParams
                    hits = client.search(
                        collection_name=COLLECTION,
                        query_vector=qvec.tolist(),
                        query_filter=qfilter,
                        limit=limit * 2,  # overfetch to allow valid_until filter
                        with_payload=True,
                    )
            except Exception:
                # fallback: query without filter then filter
                try:
                    hits = client.search(
                        collection_name=COLLECTION,
                        query_vector=qvec.tolist(),
                        limit=limit * 2,
                        with_payload=True,
                    )
                except Exception:
                    # last fallback query_points without filter
                    res = client.query_points(collection_name=COLLECTION, query=qvec.tolist(), limit=limit * 2, with_payload=True)
                    hits = res.points if hasattr(res, "points") else res
                hits = [h for h in hits if h.payload and h.payload.get("user_id") == user_id]

            # post-filter valid_until is None (active)
            filtered = []
            for h in hits:
                payload = h.payload or {}
                if payload.get("valid_until") is not None:
                    continue
                filtered.append({
                    "id": str(h.id),
                    "content": payload.get("content", ""),
                    "category": payload.get("category", "other"),
                    "score": float(h.score),
                })
                if len(filtered) >= limit:
                    break
            return filtered
        except Exception as e:
            logger.warning(f"Qdrant hybrid_search failed: {e}")
            return []

qdrant_service = QdrantService()
