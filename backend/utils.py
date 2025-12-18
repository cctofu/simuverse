import os
import json
from typing import List, Dict, Any
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


def stabilize_embeddings(X: np.ndarray) -> np.ndarray:
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    X = normalize(X, norm="l2")
    return X