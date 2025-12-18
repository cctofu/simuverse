# persona_cluster.py
from typing import List, Dict, Any, Tuple
import re
import numpy as np
from collections import Counter

from sklearn.preprocessing import StandardScaler
import umap
import hdbscan

from utils import stabilize_embeddings

# ---------------------------
# Feature engineering
# ---------------------------
def extract_numeric_scores_from_key_values(key_values: Dict[str, str]) -> Dict[str, float]:
    feats: Dict[str, float] = {}
    for k, v in key_values.items():
        if not isinstance(v, str):
            continue
        if k.strip().lower() == "demographics":
            continue

        for name, val in re.findall(r"([A-Za-z0-9_]+)\s*=\s*([-+]?\d*\.?\d+)", v):
            try:
                feats[name] = float(val)
            except ValueError:
                pass
    return feats

def build_mixed_feature_matrix(
    personas: List[Dict[str, Any]],
    w_text: float = 1.0,
    w_num: float = 2.0,
) -> np.ndarray:
    X_text = np.array([p["cluster_embedding_vector"] for p in personas], dtype=np.float32)
    X_text = stabilize_embeddings(X_text)
    norms = np.linalg.norm(X_text, axis=1, keepdims=True) + 1e-12
    X_text = (X_text / norms).astype(np.float32)

    score_dicts = [extract_numeric_scores_from_key_values(p.get("key_values", {})) for p in personas]
    all_keys = sorted({k for d in score_dicts for k in d.keys()})

    if not all_keys:
        return (w_text * X_text).astype(np.float32)

    X_num = np.full((len(personas), len(all_keys)), np.nan, dtype=np.float32)
    for i, d in enumerate(score_dicts):
        for j, key in enumerate(all_keys):
            if key in d:
                X_num[i, j] = d[key]

    col_medians = np.nanmedian(X_num, axis=0)
    inds = np.where(np.isnan(X_num))
    X_num[inds] = col_medians[inds[1]]

    X_num = StandardScaler().fit_transform(X_num).astype(np.float32)

    X = np.hstack([w_text * X_text, w_num * X_num]).astype(np.float32)
    X = stabilize_embeddings(X)
    return X

# ---------------------------
# Clustering
# ---------------------------
def assign_noise_to_nearest_cluster(labels: np.ndarray, Z: np.ndarray) -> np.ndarray:
    labels = labels.copy()
    clusters = sorted([c for c in set(labels) if c != -1])
    if not clusters:
        return labels

    centers = {c: Z[labels == c].mean(axis=0) for c in clusters}
    noise_idxs = np.where(labels == -1)[0]

    for i in noise_idxs:
        zi = Z[i]
        nearest = min(clusters, key=lambda c: float(((zi - centers[c]) ** 2).sum()))
        labels[i] = nearest
    return labels

def cluster_personas(
    personas: List[Dict[str, Any]],
    w_text: float = 1.0,
    w_num: float = 2.0,
    umap_n_neighbors: int = 20,
    umap_min_dist: float = 0.0,
    umap_n_components: int = 8,
    min_cluster_size: int = 8,
    debug: bool = True,
) -> Tuple[Dict[int, str], Dict[int, int]]:
    if len(personas) < 5:
        return {0: personas[0]["id"]}, {0: len(personas)}

    X = build_mixed_feature_matrix(personas, w_text=w_text, w_num=w_num)

    reducer = umap.UMAP(
        n_neighbors=min(umap_n_neighbors, max(2, len(personas) - 1)),
        min_dist=umap_min_dist,
        n_components=umap_n_components,
        metric="cosine",
        random_state=42,
    )
    Z = reducer.fit_transform(X).astype(np.float32)

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=2,
        metric="euclidean",
    )
    labels = clusterer.fit_predict(Z)

    if debug:
        counts = Counter(labels)
        noise_frac = counts.get(-1, 0) / len(labels)
        print("HDBSCAN label counts:", dict(counts), "noise_frac:", round(noise_frac, 3))

    labels = assign_noise_to_nearest_cluster(labels, Z)

    raw_clusters = sorted(set(labels))
    label_to_clusterid = {lab: i for i, lab in enumerate(raw_clusters)}

    cluster_rep_pids: Dict[int, str] = {}
    cluster_counts: Dict[int, int] = {}

    for lab in raw_clusters:
        cid = label_to_clusterid[lab]
        idxs = np.where(labels == lab)[0]
        cluster_counts[cid] = int(len(idxs))

        center = Z[idxs].mean(axis=0)
        rep_local = np.argmin(((Z[idxs] - center) ** 2).sum(axis=1))
        rep_idx = idxs[rep_local]
        cluster_rep_pids[cid] = personas[rep_idx]["id"]

    return cluster_rep_pids, cluster_counts

# ---------------------------
# Summaries / demographics / distributions
# ---------------------------
def fetch_consumer_summaries(
    personas: List[Dict[str, Any]],
    centroid_pids: Dict[int, str]
) -> Dict[int, Dict[str, str]]:
    pid_to_persona = {p["id"]: p for p in personas}
    out: Dict[int, Dict[str, str]] = {}
    for cluster_id, pid in centroid_pids.items():
        if pid in pid_to_persona:
            out[cluster_id] = pid_to_persona[pid].get("consumer_summary", {})
    return out

def extract_demographics(
    personas: List[Dict[str, Any]],
    centroid_pids: Dict[int, str]
) -> Dict[int, Dict[str, str]]:
    pid_to_persona = {p["id"]: p for p in personas}
    out: Dict[int, Dict[str, str]] = {}

    for cluster_id, pid in centroid_pids.items():
        if pid not in pid_to_persona:
            continue

        demographics_str = pid_to_persona[pid].get("key_values", {}).get("demographics", "")
        demo: Dict[str, str] = {}

        m = re.search(r"Gender:\s*(\w+)", demographics_str)
        if m: demo["gender"] = m.group(1)

        m = re.search(r"Age:\s*([\d\-\+]+)", demographics_str)
        if m: demo["age"] = m.group(1)

        m = re.search(r"Marital status:\s*([^\n]+)", demographics_str)
        if m: demo["marital_status"] = m.group(1).strip()

        m = re.search(r"Income:\s*([^\n]+)", demographics_str)
        if m: demo["income"] = m.group(1).strip()

        m = re.search(r"Employment status:\s*([^\n]+)", demographics_str)
        if m: demo["employment_status"] = m.group(1).strip()

        out[cluster_id] = demo

    return out

def calculate_gender_distribution(personas: List[Dict[str, Any]]) -> Dict[str, int]:
    gender_counts = {"Male": 0, "Female": 0}
    for p in personas:
        d = p.get("key_values", {}).get("demographics", "")
        if "Gender: Male" in d:
            gender_counts["Male"] += 1
        elif "Gender: Female" in d:
            gender_counts["Female"] += 1
    return gender_counts

def calculate_age_distribution(personas: List[Dict[str, Any]]) -> Dict[str, int]:
    age_counts = {"18-29": 0, "30-49": 0, "50-64": 0, "65+": 0}
    for p in personas:
        d = p.get("key_values", {}).get("demographics", "")
        if "Age: 18-29" in d:
            age_counts["18-29"] += 1
        elif "Age: 30-49" in d:
            age_counts["30-49"] += 1
        elif "Age: 50-64" in d:
            age_counts["50-64"] += 1
        elif "Age: 65+" in d:
            age_counts["65+"] += 1
    return age_counts
