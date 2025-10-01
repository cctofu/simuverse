#!/usr/bin/env python3
"""
9_evaluate_clusters.py — Evaluate clustering quality and stability.

Inputs:
  - users_features.npy  (from 34.py)
  - user_personas.csv   (labels from 56.py)
  - (optional) Z.npy    (reduced features if you saved them in 56.py; else we compute PCA-50)

Outputs:
  - cluster_eval.json   (metrics summary)
  - cluster_sizes.csv   (size distribution)
"""

import argparse
import json
import numpy as np
import pandas as pd
from sklearn.metrics import silhouette_score, davies_bouldin_score, adjusted_rand_score
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans

def main():
    ap = argparse.ArgumentParser(description="Evaluate clustering metrics and stability")
    ap.add_argument("--features", default="users_features.npy")
    ap.add_argument("--labels-csv", default="user_personas.csv")
    ap.add_argument("--reduced", default="", help="Optional path to reduced matrix (Z.npy)")
    ap.add_argument("--stability-runs", type=int, default=5)
    ap.add_argument("--stability-subsample", type=float, default=0.8)
    ap.add_argument("--out-json", default="cluster_eval.json")
    ap.add_argument("--out-sizes", default="cluster_sizes.csv")
    args = ap.parse_args()

    X = np.load(args.features)
    labels_df = pd.read_csv(args.labels_csv)
    labels = labels_df["cluster"].values

    # Filter out noise (-1) for metrics that require well-defined clusters
    mask = labels != -1
    Xm = X[mask]
    ym = labels[mask]

    # Use provided reduced matrix if available, else PCA(50) just for metrics speed
    if args.reduced:
        Zall = np.load(args.reduced)
        Z = Zall[mask]
    else:
        Z = PCA(n_components=min(50, Xm.shape[1]), random_state=42).fit_transform(Xm)

    metrics = {}
    if len(np.unique(ym)) >= 2 and len(ym) > 100:
        try:
            metrics["silhouette"] = float(silhouette_score(Z, ym, metric="euclidean"))
        except Exception:
            metrics["silhouette"] = None
        try:
            metrics["davies_bouldin"] = float(davies_bouldin_score(Z, ym))
        except Exception:
            metrics["davies_bouldin"] = None
    else:
        metrics["silhouette"] = None
        metrics["davies_bouldin"] = None

    # Size distribution
    sizes = pd.Series(labels).value_counts().sort_index()
    sizes.to_frame(name="size").to_csv(args.out_sizes)

    # Stability via sub-sampling + KMeans on Z (proxy)
    # (We compare original labels against new KMeans labels after aligning via best-k)
    stability_scores = []
    uniq = np.unique(ym)
    k = max(2, len(uniq))
    for _ in range(args.stability_runs):
        n = int(args.stability_subsample * len(Z))
        idx = np.random.choice(len(Z), n, replace=False)
        km = KMeans(n_clusters=k, n_init="auto", random_state=42)
        y_new = km.fit_predict(Z[idx])
        # Compare with original labels subset; need a proxy alignment:
        # Use adjusted_rand_score (label-invariant)
        y_ref = ym[idx]
        ari = adjusted_rand_score(y_ref, y_new)
        stability_scores.append(float(ari))
    metrics["stability_ari_mean"] = float(np.mean(stability_scores)) if stability_scores else None
    metrics["stability_ari_std"] = float(np.std(stability_scores)) if stability_scores else None

    with open(args.out_json, "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"Saved metrics: {args.out_json}")
    print(f"Saved sizes:   {args.out_sizes}")
    print("Metrics:", metrics)

if __name__ == "__main__":
    main()
