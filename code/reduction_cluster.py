#!/usr/bin/env python3
import argparse
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
import colorful as cf

# ---------- helpers ----------
import numpy as np

def sanitize_features(X: np.ndarray, clip=1e6) -> np.ndarray:
    """
    Make X safe for PCA/KMeans:
    - float32 contiguous
    - replace NaN/±Inf with 0
    - clip extreme magnitudes
    """
    X = np.asarray(X, dtype=np.float32, order="C")
    # replace NaN/Inf
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    # clip big values to avoid overflow in matmul
    if clip is not None:
        np.clip(X, -clip, clip, out=X)
    return X

def reduce_features_pca(X, pca_dims=64, seed=42):
    """Robust PCA -> float32."""
    X = sanitize_features(X)
    p = PCA(
        n_components=min(pca_dims, X.shape[1]),
        random_state=seed,
        svd_solver="randomized",   # more stable/faster for large, high-D data
    )
    Z = p.fit_transform(X)
    return Z.astype(np.float32, copy=False)

def cluster_kmeans(Z, k=8, seed=42):
    Z = sanitize_features(Z)  # extra safety
    km = KMeans(n_clusters=k, random_state=seed, n_init=10, algorithm="elkan")
    return km.fit_predict(Z)

def top_terms_per_cluster(texts, labels, top_k=10):
    df = pd.DataFrame({"text": texts, "cluster": labels})
    vec = TfidfVectorizer(max_features=20000, ngram_range=(1, 2), min_df=3, stop_words="english")
    Xs = vec.fit_transform(df["text"].fillna(""))
    vocab = np.array(vec.get_feature_names_out())

    terms = {}
    for cid, grp in df.groupby("cluster"):
        idx = grp.index.values
        mean_tfidf = np.asarray(Xs[idx].mean(axis=0)).ravel()
        top_idx = mean_tfidf.argsort()[-top_k:][::-1]
        terms[int(cid)] = vocab[top_idx].tolist()
    return terms

def summarize_clusters(meta_df, labels):
    tmp = meta_df.copy()
    tmp["cluster"] = labels
    out = []
    for cid, g in tmp.groupby("cluster"):
        out.append({
            "cluster": int(cid),
            "size": int(len(g)),
            "median_rating": float(g["avg_rating"].median()) if pd.notnull(g["avg_rating"].median()) else None,
            "avg_rating": float(g["avg_rating"].mean()) if pd.notnull(g["avg_rating"].mean()) else None,
            "pct_verified": float(g["pct_verified_purchase"].mean()) if pd.notnull(g["pct_verified_purchase"].mean()) else None,
            "avg_helpful_votes": float(g["avg_helpful_votes"].mean()) if pd.notnull(g["avg_helpful_votes"].mean()) else None,
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

# ---------- main ----------

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Robust PCA + KMeans clustering for user personas")
    ap.add_argument("--meta", default="./data/users_meta.csv")
    ap.add_argument("--features", default="./data/users_features.npy")
    ap.add_argument("--pca-dims", type=int, default=64)
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--out-users", default="./data/user_personas.csv")
    ap.add_argument("--out-clusters", default="./data/cluster_summary.csv")
    args = ap.parse_args()

    print(cf.bold(cf.green("Begin PCA + KMeans (robust) ...")))
    meta = pd.read_csv(args.meta)
    X = np.load(args.features)
    print(cf.bold(cf.green(f"Loaded features: shape={X.shape}, dtype={X.dtype}")))

    # Sanity report before PCA
    finite_ratio = np.isfinite(X).mean()
    print(cf.bold(cf.green(f"Finite values ratio: {finite_ratio:.6f}")))
    if finite_ratio < 1.0:
        print(cf.bold(cf.yellow("Non-finite values detected; sanitizing...")))

    # PCA
    Z = reduce_features_pca(X, pca_dims=args.pca_dims, seed=42)
    print(cf.bold(cf.green(f"PCA reduced features to shape={Z.shape}")))

    # KMeans
    labels = cluster_kmeans(Z, k=args.k, seed=42)
    print(cf.bold(cf.green("Finished KMeans clustering")))

    # Describe clusters
    terms = top_terms_per_cluster(meta["concat_text"].fillna(""), labels, top_k=10)
    stats = summarize_clusters(meta, labels)
    persona_labels = build_persona_labels(terms, stats)

    # Per-user outputs
    label_series = pd.Series(labels, index=meta.index)
    pretty = label_series.map(lambda c: persona_labels.get(c, f"cluster-{c}"))

    users_out = meta[["user_id", "concat_text", "avg_rating",
                      "pct_verified_purchase", "avg_helpful_votes"]].copy()
    users_out["cluster"] = labels
    users_out["persona_label"] = pretty

    # Save
    users_out.to_csv(args.out_users, index=False)
    stats["top_terms"] = stats["cluster"].map(lambda c: ", ".join(terms.get(c, [])))
    stats["persona_label"] = stats["cluster"].map(lambda c: persona_labels.get(c, f"cluster-{c}"))
    stats.to_csv(args.out_clusters, index=False)

    print(cf.bold(cf.green(f"Saved per-user assignments: {args.out_users}")))
    print(cf.bold(cf.green(f"Saved cluster summary:      {args.out_clusters}")))
