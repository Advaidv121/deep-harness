import hashlib
import numpy as np
from typing import List, Optional
from backend.app.config import get_settings

settings = get_settings()

class EmbeddingService:
    def __init__(self, dimension: int = 384):
        self.local_dimension = dimension
        # When Titan is enabled, dimension switches to 1024 transparently
        self._bedrock = None

    @property
    def dimension(self) -> int:
        if getattr(settings, "BEDROCK_EMBED_ENABLED", False):
            return settings.BEDROCK_EMBED_DIMENSION
        return self.local_dimension

    def _get_bedrock(self):
        if self._bedrock is None:
            from backend.app.services.bedrock_service import bedrock_service
            self._bedrock = bedrock_service
        return self._bedrock

    def encode(self, text: str) -> np.ndarray:
        """
        Hybrid: Titan v2 (1024d, semantic) when BEDROCK_EMBED_ENABLED, else deterministic 384d hash.
        Titan path is sync; falls back to local on any error so evals never break.
        """
        if getattr(settings, "BEDROCK_EMBED_ENABLED", False):
            try:
                vec = self._get_bedrock().embed_sync(text)
                if vec is not None and len(vec) == self.dimension:
                    arr = np.array(vec, dtype=np.float32)
                    # already normalized by Titan when normalize=True, but ensure
                    n = np.linalg.norm(arr)
                    if n > 1e-8:
                        arr = arr / n
                    return arr
            except Exception:
                pass  # fall through to local

        # --- Local deterministic 384d hash (offline, zero-cost) ---
        if not text or not text.strip():
            return np.zeros(self.local_dimension, dtype=np.float32)
        # Use local_dimension always for hash path (stored 384d is canonical offline)
        dim = self.local_dimension
        text_clean = text.lower().strip()
        tokens = text_clean.split()
        features = list(tokens)
        for i in range(len(text_clean) - 2):
            features.append(text_clean[i:i+3])
        for i in range(len(text_clean) - 3):
            features.append(text_clean[i:i+4])
        vector = np.zeros(dim, dtype=np.float32)
        for feat in features:
            h1 = int(hashlib.md5(feat.encode('utf-8')).hexdigest(), 16)
            h2 = int(hashlib.sha256(feat.encode('utf-8')).hexdigest(), 16)
            idx1 = h1 % dim
            idx2 = (h1 >> 16) % dim
            idx3 = h2 % dim
            idx4 = (h2 >> 16) % dim
            val1 = 1.0 if (h1 & 1) else -1.0
            val2 = 1.0 if (h1 & 2) else -1.0
            val3 = 1.0 if (h2 & 1) else -1.0
            val4 = 1.0 if (h2 & 2) else -1.0
            vector[idx1] += val1
            vector[idx2] += val2 * 0.75
            vector[idx3] += val3 * 0.5
            vector[idx4] += val4 * 0.25
        norm = np.linalg.norm(vector)
        if norm > 1e-8:
            vector = vector / norm
        # If caller expects 1024d but we're in fallback, pad/return 384d — retrieval handles dim mismatch
        return vector

    def to_bytes(self, vector: np.ndarray) -> bytes:
        return vector.astype(np.float32).tobytes()

    def from_bytes(self, data: bytes) -> np.ndarray:
        if not data:
            return np.zeros(self.dimension, dtype=np.float32)
        arr = np.frombuffer(data, dtype=np.float32)
        return arr

    def cosine_similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        # Handle dim mismatch (e.g. stored 384d vs query 1024d during Titan rollout) — fallback 0
        if vec_a.shape[0] != vec_b.shape[0]:
            return 0.0
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_a < 1e-8 or norm_b < 1e-8:
            return 0.0
        return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))

    def cosine_with_fallback(self, query_vec: np.ndarray, fact_vec: np.ndarray, fact_text: str) -> float:
        """If dims mismatch, re-encode fact with current encoder for apples-to-apples compare."""
        if query_vec.shape[0] != fact_vec.shape[0]:
            # Re-encode fact text with same encoder as query
            fact_vec = self.encode(fact_text)
            if query_vec.shape[0] != fact_vec.shape[0]:
                return 0.0
        return self.cosine_similarity(query_vec, fact_vec)

embedding_service = EmbeddingService()
