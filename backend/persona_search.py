# persona_search.py
from typing import List, Dict, Any, Tuple
import numpy as np
from openai import OpenAI

from utils import load_personas, l2_normalize
from config import EMBEDDING_MODEL, DATABASE_PATH

_PERSONA_INDEX = None  # (M, meta_list)

def embed_query(client: OpenAI, text: str) -> List[float]:
    resp = client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return l2_normalize(resp.data[0].embedding)

def _row_l2_normalize(M: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(M, axis=1, keepdims=True) + 1e-12
    return (M / norms).astype(np.float32)

def _build_persona_index(personas: List[Dict[str, Any]]) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
    mat = []
    meta_list = []
    for p in personas:
        ev = p.get("embedding_vector")
        if not ev:
            continue
        mat.append(ev)
        meta_list.append(p)

    M = np.array(mat, dtype=np.float32)
    M = _row_l2_normalize(M)
    return M, meta_list

def get_persona_index_cached() -> Tuple[np.ndarray, List[Dict[str, Any]]]:
    """
    Loads personas and builds the embedding matrix once per Python process.
    """
    global _PERSONA_INDEX
    if _PERSONA_INDEX is None:
        personas = load_personas(DATABASE_PATH)
        _PERSONA_INDEX = _build_persona_index(personas)
    return _PERSONA_INDEX

def rank_personas_fast(
    query_vec: List[float],
    M: np.ndarray,
    meta_list: List[Dict[str, Any]],
    top_k: int
) -> List[Dict[str, Any]]:
    q = np.array(query_vec, dtype=np.float32)
    q = q / (np.linalg.norm(q) + 1e-12)

    scores = M @ q

    k = min(max(1, top_k), scores.shape[0])
    top_idx = np.argpartition(-scores, k - 1)[:k]
    top_idx = top_idx[np.argsort(-scores[top_idx])]

    out = []
    for i in top_idx:
        p = meta_list[int(i)]
        out.append({
            "id": p.get("id"),
            "score": float(scores[int(i)]),
            "embedding_profile_text": p.get("embedding_profile_text", ""),
            "key_values": p.get("key_values", {}),
            "consumer_summary": p.get("consumer_summary", {}),
            "cluster_embedding_vector": p.get("cluster_embedding_vector", []),
        })
    return out
