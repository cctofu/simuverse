#!/usr/bin/env python3
"""
34.py — Build user-level embeddings and features.

Requires input: user_profiles.csv from the combined step (user_id, concat_text, numeric features).
Outputs:
  - users_meta.csv         (user_id, concat_text, raw numeric stats preserved)
  - users_features.npy     (numpy array: [embedding || scaled_behavior])

Embedding backends:
  --backend minilm      (default, local sentence-transformers/all-MiniLM-L6-v2)
  --backend openai      (uses OpenAI embeddings; requires OPENAI_API_KEY env var)
"""

import os
import argparse
import json
import numpy as np
import pandas as pd
from tqdm import tqdm
from sklearn.preprocessing import StandardScaler

# Optional imports guarded by backend selection
def _embed_minilm(texts, model_name="sentence-transformers/all-MiniLM-L6-v2", batch_size=64):
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(model_name)
    return model.encode(texts, batch_size=batch_size, show_progress_bar=True, normalize_embeddings=True)

def _embed_openai(texts, model_name="text-embedding-3-small", batch_size=1000):
    """
    Uses OpenAI embeddings (one request per text for simplicity).
    Set OPENAI_API_KEY in env. Requires 'openai' package >= 1.0.
    """
    try:
        from openai import OpenAI
    except Exception as e:
        raise RuntimeError("Install openai>=1.0 to use --backend openai") from e

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    vecs = []
    for t in tqdm(texts, desc="OpenAI embeddings"):
        # Truncate excessively long texts defensively
        if len(t) > 6000:
            t = t[:6000]
        resp = client.embeddings.create(model=model_name, input=t)
        vecs.append(resp.data[0].embedding)
    return np.array(vecs, dtype=np.float32)

def normalize_text(s: str) -> str:
    import re
    s = (s or "").lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s

def main():
    ap = argparse.ArgumentParser(description="Create user-level embeddings + features")
    ap.add_argument("--in-users", default="user_profiles.csv", help="Input CSV from previous step")
    ap.add_argument("--backend", choices=["minilm", "openai"], default="minilm", help="Embedding backend")
    ap.add_argument("--minilm-model", default="sentence-transformers/all-MiniLM-L6-v2",
                    help="Sentence-Transformers model (if backend=minilm)")
    ap.add_argument("--openai-model", default="text-embedding-3-small",
                    help="OpenAI embedding model (if backend=openai)")
    ap.add_argument("--out-meta", default="users_meta.csv", help="Output CSV with user meta")
    ap.add_argument("--out-npy", default="users_features.npy", help="Output NPY feature matrix")
    ap.add_argument("--no-scale", action="store_true", help="Disable scaling of numeric features")
    args = ap.parse_args()

    # Load user profiles
    df = pd.read_csv(args.in_users)
    required_cols = [
        "user_id", "concat_text",
        "num_reviews", "avg_rating", "std_rating",
        "frac_low", "frac_high", "avg_helpful_votes",
        "pct_verified_purchase", "pct_with_images"
    ]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in {args.in_users}: {missing}")

    # Normalize text (light)
    df["concat_text"] = df["concat_text"].fillna("").map(normalize_text)

    # Prepare texts for embedding
    texts = df["concat_text"].tolist()

    # Embeddings
    if args.backend == "minilm":
        E = _embed_minilm(texts, model_name=args.minilm_model)
    else:
        # Backend: openai
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY not set in environment.")
        E = _embed_openai(texts, model_name=args.openai_model)

    # Numeric/behavior features
    num_cols = [
        "num_reviews", "avg_rating", "std_rating",
        "frac_low", "frac_high", "avg_helpful_votes",
        "pct_verified_purchase", "pct_with_images"
    ]
    X_num = df[num_cols].copy()
    # Clip a bit to reduce outliers
    X_num["avg_helpful_votes"] = X_num["avg_helpful_votes"].clip(0, 200)

    if not args.no_scale:
        scaler = StandardScaler()
        Xs = scaler.fit_transform(X_num.values)
    else:
        Xs = X_num.values

    # Final features = [embedding || numeric]
    X = np.hstack([E, Xs]).astype(np.float32)

    # Save meta + features
    meta_cols = ["user_id", "concat_text"] + num_cols
    df[meta_cols].to_csv(args.out_meta, index=False)
    np.save(args.out_npy, X)

    print(f"Saved meta: {args.out_meta}")
    print(f"Saved features: {args.out_npy} (shape={X.shape})")

if __name__ == "__main__":
    main()
