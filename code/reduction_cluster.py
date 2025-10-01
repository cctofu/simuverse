#!/usr/bin/env python3
"""
56.py — Dimensionality reduction + clustering + auto-labeling (user personas).

Inputs (from 34.py):
  - users_meta.csv        (user_id, concat_text, numeric stats)
  - users_features.npy    (np.array: [embedding || scaled_behavior])

Outputs:
  - user_personas.csv     (user_id, cluster, persona_label, basic stats)
  - cluster_summary.csv   (per-cluster size, median/avg stats, top terms)
  - (optional) Z.npy      (reduced features if --save-reduced)
"""

import argparse
import numpy as np
import pandas as pd

from sklearn.decomposition import PCA
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

try:
    import umap
except Exception:
    umap = None

try:
    import hdbscan
except Exception:
    hdbscan = None


def reduce_features(X, use_umap=True, n_umap=50, n_neighbors=30, metric="cosine", seed=42, pca_first=False, pca_dims=128):
    Z = X
    if pca_first:
        p = PCA(n_components=min(pca_dims, X.shape[1]), random_state=seed)
        Z = p.fit_transform(Z)
    if use_umap:
        if umap is None:
            raise RuntimeError("umap-learn not installed. Install with: pip install umap-learn")
        reducer = umap.UMAP(n_neighbors=n_neighbors, n_components=n_umap, min_dist=0.0,
                            metric=metric, random_state=seed)
        Z = reducer.fit_transform(Z)
    return Z


def cluster_data(Z, algo="hdbscan", min_cluster_size=40, min_samples=None, k=8, seed=42):
    if algo == "hdbscan":
        if hdbscan is None:
            raise RuntimeError("hdbscan not installed. Install with: pip install hdbscan")
        clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size,
                                    min_samples=min_samples,
                                    metric="euclidean",
                                    cluster_selection_method="eom",
                                    prediction_data=True)
        labels = clusterer.fit_predict(Z)
        return labels
    else:
        km = KMeans(n_clusters=k, random_state=seed, n_init="auto")
        labels = km.fit_predict(Z)
        return labels


def top_terms_per_cluster(texts, labels, top_k=10):
    df = pd.DataFrame({"text": texts, "cluster": labels})
    df_nc = df[df["cluster"] != -1].copy()
    if df_nc.empty:
        return {}

    vec = TfidfVectorizer(max_features=20000, ngram_range=(1,2), min_df=3, stop_words="english")
    X = vec.fit_transform(df_nc["text"].fillna(""))

    vocab = np.array(vec.get_feature_names_out())
    terms = {}
    for cid, grp in df_nc.groupby("cluster"):
        idx = grp.index.values
        mean_tfidf = np.asarray(X[df_nc.index.get_indexer(idx)].mean(axis=0)).ravel()
        top_idx = mean_tfidf.argsort()[-top_k:][::-1]
        terms[int(cid)] = vocab[top_idx].tolist()
    return terms


def summarize_clusters(meta_df, labels):
    out = []
    tmp = meta_df.copy()
    tmp["cluster"] = labels
    for cid, g in tmp.groupby("cluster"):
        size = len(g)
        med_rating = g["avg_rating"].median()
        avg_rating = g["avg_rating"].mean()
        pct_verified = g["pct_verified_purchase"].mean()
        avg_helpful = g["avg_helpful_votes"].mean()
        out.append({
            "cluster": int(cid),
            "size": int(size),
            "median_rating": float(med_rating) if pd.notnull(med_rating) else None,
            "avg_rating": float(avg_rating) if pd.notnull(avg_rating) else None,
            "pct_verified": float(pct_verified),
            "avg_helpful_votes": float(avg_helpful)
        })
    return pd.DataFrame(out).sort_values("size", ascending=False)


def build_persona_labels(cluster_terms, cluster_stats):
    stats = cluster_stats.set_index("cluster").to_dict(orient="index")
    labels = {}
    for cid, terms in cluster_terms.items():
        r = stats.get(cid, {})
        rating = r.get("median_rating", None)
        if rating is None:
            sentiment = "mixed-rating"
        elif rating <= 2.5:
            sentiment = "low-rating"
        elif rating >= 4.0:
            sentiment = "high-rating"
        else:
            sentiment = "mixed-rating"
        key_terms = " / ".join(terms[:3]) if terms else ""
        labels[cid] = f"{sentiment} • {key_terms}".strip(" •")
    return labels


def main():
    ap = argparse.ArgumentParser(description="Reduce + cluster + label user features")
    ap.add_argument("--meta", default="users_meta.csv", help="Meta CSV from 34.py")
    ap.add_argument("--features", default="users_features.npy", help="NPY features from 34.py")
    ap.add_argument("--use-umap", action="store_true", help="Enable UMAP reduction")
    ap.add_argument("--n-umap", type=int, default=50, help="UMAP components (if enabled)")
    ap.add_argument("--n-neighbors", type=int, default=30, help="UMAP n_neighbors")
    ap.add_argument("--pca-first", action="store_true", help="Apply PCA before UMAP")
    ap.add_argument("--pca-dims", type=int, default=128, help="PCA dimensions if --pca-first")
    ap.add_argument("--algo", choices=["hdbscan", "kmeans"], default="hdbscan", help="Clustering algorithm")
    ap.add_argument("--min-cluster-size", type=int, default=40, help="HDBSCAN min_cluster_size")
    ap.add_argument("--min-samples", type=int, default=None, help="HDBSCAN min_samples (optional)")
    ap.add_argument("--k", type=int, default=8, help="K for KMeans (if --algo kmeans)")
    ap.add_argument("--save-reduced", type=str, default="", help="Optional path to save reduced matrix (Z.npy)")
    ap.add_argument("--out-users", default="user_personas.csv", help="Output per-user assignments")
    ap.add_argument("--out-clusters", default="cluster_summary.csv", help="Output per-cluster summary")
    args = ap.parse_args()

    meta = pd.read_csv(args.meta)
    X = np.load(args.features)

    # Reduce (optional)
    Z = reduce_features(
        X,
        use_umap=args.use_umap,
        n_umap=args.n_umap,
        n_neighbors=args.n_neighbors,
        metric="cosine",
        seed=42,
        pca_first=args.pca_first,
        pca_dims=args.pca_dims
    )

    if args.save_reduced:
        np.save(args.save_reduced, Z)
        print(f"Saved reduced features to {args.save_reduced} (shape={Z.shape})")

    # Cluster
    labels = cluster_data(
        Z,
        algo=args.algo,
        min_cluster_size=args.min_cluster_size,
        min_samples=args.min_samples,
        k=args.k,
        seed=42
    )

    # Describe clusters
    terms = top_terms_per_cluster(meta["concat_text"].fillna(""), labels, top_k=10)
    stats = summarize_clusters(meta, labels)
    persona_labels = build_persona_labels(terms, stats)

    # Map labels; hdbscan noise = -1
    label_series = pd.Series(labels, index=meta.index)
    pretty = label_series.map(lambda c: persona_labels.get(c, "noise/outlier"))

    users_out = meta[["user_id", "concat_text", "avg_rating", "pct_verified_purchase", "avg_helpful_votes"]].copy()
    users_out["cluster"] = labels
    users_out["persona_label"] = pretty

    # Save
    users_out.to_csv(args.out_users, index=False)
    stats["top_terms"] = stats["cluster"].map(lambda c: ", ".join(terms.get(c, [])))
    stats["persona_label"] = stats["cluster"].map(lambda c: persona_labels.get(c, "noise/outlier"))
    stats.to_csv(args.out_clusters, index=False)

    print(f"Saved per-user assignments: {args.out_users}")
    print(f"Saved cluster summary:      {args.out_clusters}")

if __name__ == "__main__":
    main()
