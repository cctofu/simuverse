import os
import json
from typing import List, Dict, Any
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from openai import OpenAI
import numpy as np
from sklearn.preprocessing import normalize


def load_personas(db_path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database file not found: {db_path}")
    with open(db_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Database JSON should be a list of persona objects.")
    return data


def l2_normalize(v: List[float]) -> List[float]:
    arr = np.asarray(v, dtype="float32")
    norm = np.linalg.norm(arr)
    return (arr / norm).tolist() if norm > 0 else arr.tolist()


def cosine_sim(a: List[float], b: List[float]) -> float:
    va, vb = np.asarray(a, dtype="float32"), np.asarray(b, dtype="float32")
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    return float(np.dot(va, vb) / denom) if denom > 0 else 0.0


def ensure_persona_vectors(personas: List[Dict[str, Any]]) -> None:
    """Ensure all personas have both embedding_vector and cluster_embedding_vector."""
    missing = [p.get("id") for p in personas if not p.get("embedding_vector")]
    if missing:
        raise ValueError(f"Missing 'embedding_vector' for: {missing[:10]} ...")
    missing_cluster = [p.get("id") for p in personas if not p.get("cluster_embedding_vector")]
    if missing_cluster:
        raise ValueError(f"Missing 'cluster_embedding_vector' for: {missing_cluster[:10]} ...")
    for p in personas:
        p["embedding_vector"] = l2_normalize(p["embedding_vector"])
        p["cluster_embedding_vector"] = l2_normalize(p["cluster_embedding_vector"])


def stabilize_embeddings(X: np.ndarray) -> np.ndarray:
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    X = normalize(X, norm="l2")
    return X