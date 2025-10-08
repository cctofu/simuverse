#!/usr/bin/env python3
"""
Fast product clustering on Apple Silicon (MPS) with SentenceTransformers + HDBSCAN.

- Auto-detects Apple GPU (MPS) and uses it by default (or pass --device mps).
- Caches embeddings on disk keyed by model+titles hash.
- PCA to 50D before HDBSCAN for much faster clustering.

Install:
  pip install pandas numpy sentence-transformers hdbscan scikit-learn
  pip install --upgrade torch  # make sure PyTorch has MPS support

Run:
  python build_clusters.py \
    --input ./data/product_review.csv \
    --output ./code/products_clustered.csv \
    --summary ./code/clusters_summary.csv \
    --model sentence-transformers/paraphrase-MiniLM-L6-v2 \
    --min-cluster-size 15 \
    --metric euclidean \
    --device mps
"""
import argparse, os, sys, warnings, hashlib, time, json
from collections import Counter

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
import hdbscan
from sklearn.decomposition import PCA
import torch


# --------------------------- IO ---------------------------

def read_data(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Input CSV not found: {path}")
    df = pd.read_csv(path)
    if "title_y" not in df.columns:
        raise ValueError("Input CSV must contain a 'title_y' column (product title).")
    df["title_y"] = df["title_y"].astype(str).fillna("").str.strip()
    before = len(df)
    df = df[df["title_y"].str.len() > 0].copy()
    dropped = before - len(df)
    if dropped > 0:
        warnings.warn(f"Dropped {dropped} rows with empty title_y.")
    return df


# ---------------------- Device Handling -------------------

def detect_device(user_device: str = "") -> str:
    """
    Resolve device preference: user flag > CUDA > MPS (Apple) > CPU.
    """
    if user_device:
        return user_device
    if torch is not None:
        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
    return "cpu"


# -------------------- Embedding Cache ---------------------

def _titles_fingerprint(titles: list[str], model_name: str) -> str:
    h = hashlib.sha256()
    h.update(model_name.encode("utf-8"))
    for t in titles:
        h.update(b"\x00")
        h.update(t.encode("utf-8", errors="ignore"))
    return h.hexdigest()[:16]

def load_cached_embeddings(cache_dir: str, fp: str):
    if not cache_dir:
        return None
    npy = os.path.join(cache_dir, f"emb_{fp}.npy")
    if os.path.exists(npy):
        try:
            emb = np.load(npy)
            return emb
        except Exception:
            return None
    return None

def save_cached_embeddings(cache_dir: str, fp: str, emb: np.ndarray):
    if not cache_dir:
        return
    os.makedirs(cache_dir, exist_ok=True)
    np.save(os.path.join(cache_dir, f"emb_{fp}.npy"), emb)


# -------------------- Embeddings + PCA --------------------

def build_embeddings(titles: list[str], model_name: str, batch_size: int, device: str, cache_dir: str | None):
    fp = _titles_fingerprint(titles, model_name)
    cached = load_cached_embeddings(cache_dir, fp) if cache_dir else None
    if cached is not None:
        print(f"[cache] Loaded embeddings (shape={cached.shape})")
        return cached

    device_resolved = detect_device(device)
    print(f"[embed] Using device: {device_resolved}")
    model = SentenceTransformer(model_name, device=device_resolved)

    t0 = time.time()
    emb = model.encode(
        titles,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,  # euclidean ~ cosine
    )
    t1 = time.time()
    print(f"[embed] Encoded {len(titles)} titles in {t1 - t0:.1f}s; dim={emb.shape[1]}")
    save_cached_embeddings(cache_dir, fp, emb)
    return emb

def reduce_dimensionality(X: np.ndarray, target_dim: int = 50, random_state: int = 42) -> np.ndarray:
    if X.shape[1] <= target_dim:
        return X
    t0 = time.time()
    pca = PCA(n_components=target_dim, random_state=random_state)
    Xr = pca.fit_transform(X)
    t1 = time.time()
    print(f"[pca] Reduced {X.shape[1]}→{target_dim} in {t1 - t0:.1f}s (explained var ≈ {pca.explained_variance_ratio_.sum():.2f})")
    return Xr


# ----------------------- Clustering -----------------------

def run_hdbscan(embeddings: np.ndarray, min_cluster_size: int, min_samples: int | None, metric: str, n_jobs: int):
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric=metric,
        cluster_selection_method="eom",
        prediction_data=False,
        approx_min_span_tree=True,     # speed
        core_dist_n_jobs=n_jobs,       # parallelism
    )
    t0 = time.time()
    labels = clusterer.fit_predict(embeddings)
    t1 = time.time()
    print(f"[hdbscan] {embeddings.shape[0]} points clustered in {t1 - t0:.1f}s "
          f"→ {len(set(labels)) - (1 if -1 in labels else 0)} clusters; noise={int((labels==-1).sum())}")
    return labels

def remap_labels(labels: np.ndarray, keep_noise_minus_one: bool) -> np.ndarray:
    unique = sorted(set(labels))
    if keep_noise_minus_one:
        pos = [u for u in unique if u >= 0]
        mapping = {lab: i for i, lab in enumerate(pos)}
        return np.array([lab if lab == -1 else mapping[lab] for lab in labels], dtype=int)
    pos = [u for u in unique if u >= 0]
    mapping = {lab: i for i, lab in enumerate(pos)}
    if -1 in unique:
        mapping[-1] = len(pos)
    return np.array([mapping[lab] for lab in labels], dtype=int)

def pick_exemplar_titles(labels: np.ndarray, titles: list[str]) -> dict[int, str]:
    df = pd.DataFrame({"label": labels, "title": titles})
    exemplars = {}
    for lab, group in df.groupby("label"):
        counts = Counter(group["title"])
        most = counts.most_common()
        if not most:
            exemplars[lab] = ""
            continue
        top = most[0][1]
        cands = [t for t, c in most if c == top]
        cands.sort(key=len)
        exemplars[lab] = cands[0]
    return exemplars


# -------------------------- Main --------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="./data/product_review.csv")
    ap.add_argument("--output", default="./code/products_clustered.csv")
    ap.add_argument("--summary", default="./code/clusters_summary.csv")
    ap.add_argument("--model", default="sentence-transformers/paraphrase-MiniLM-L6-v2")
    ap.add_argument("--batch-size", type=int, default=256)
    ap.add_argument("--device", default="")  # '', 'mps', 'cuda', 'cpu'
    ap.add_argument("--min-cluster-size", type=int, default=15)
    ap.add_argument("--min-samples", type=int, default=None)
    ap.add_argument("--metric", default="euclidean", choices=["euclidean", "cosine"])
    ap.add_argument("--keep-noise-minus-one", action="store_true")
    ap.add_argument("--cache-dir", default=".emb_cache")     # where to store embeddings
    ap.add_argument("--pca-dim", type=int, default=50)       # 0/None to disable PCA
    args = ap.parse_args()

    # Read
    df = read_data(args.input)

    # Unique titles -> embed once
    unique_titles = df["title_y"].drop_duplicates().reset_index(drop=True)
    title_to_uid = {t: i for i, t in enumerate(unique_titles)}

    # Embeddings (MPS if available)
    emb = build_embeddings(unique_titles.tolist(), args.model, args.batch_size, args.device, args.cache_dir)
    print(f"[info] Embeddings shape: {emb.shape}")

    # PCA (big speedup for HDBSCAN)
    X = reduce_dimensionality(emb, target_dim=args.pca_dim or emb.shape[1])

    # HDBSCAN
    n_jobs = max(1, os.cpu_count() or 1)
    labels_unique = run_hdbscan(X, args.min_cluster_size, args.min_samples, args.metric, n_jobs)

    # Remap labels if desired
    labels_mapped = remap_labels(labels_unique, keep_noise_minus_one=args.keep_noise_minus_one)

    # Map back to rows
    uid_to_cluster = {i: labels_mapped[i] for i in range(len(unique_titles))}
    df["product_cluster"] = df["title_y"].map(lambda t: uid_to_cluster[title_to_uid[t]]).astype(int)

    # Summary
    summary_path = args.summary or f"{os.path.splitext(args.output)[0]}.clusters.csv"
    sizes = Counter(labels_mapped.tolist())
    exemplars = pick_exemplar_titles(labels_mapped, unique_titles.tolist())
    pd.DataFrame(
        [{"cluster_id": lab, "size": sizes[lab], "exemplar_title": exemplars.get(lab, "")}
         for lab in sorted(sizes.keys())]
    ).sort_values("size", ascending=False).to_csv(summary_path, index=False)

    # Save
    df.to_csv(args.output, index=False)
    n_clusters = len([c for c in set(labels_mapped) if c >= 0])
    print(f"[done] {n_clusters} clusters. Updated CSV → {args.output}")
    print(f"[done] Summary CSV → {summary_path}")


if __name__ == "__main__":
    main()
