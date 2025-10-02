import os
import argparse
import numpy as np
import pandas as pd
from tqdm import tqdm
from dotenv import load_dotenv
from sklearn.preprocessing import StandardScaler
from openai import OpenAI
from utils import normalize_text
import colorful as cf
load_dotenv()

# -------------------------
# Embedding backends
# -------------------------
def _embed_minilm(
    texts,
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    batch_size=256,        # bigger batches = less overhead
    normalize=True
):
    import os
    from sentence_transformers import SentenceTransformer

    # Enable tokenizer parallelism
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "true")

    # Load model on CPU
    model = SentenceTransformer(model_name, device="cpu")
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        normalize_embeddings=normalize,
        convert_to_numpy=True,
    )
    return embeddings


def _embed_openai(texts, model_name):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    vecs = []
    for t in tqdm(texts, desc="OpenAI embeddings"):
        if t and len(t) > 6000:
            t = t[:6000]
        resp = client.embeddings.create(model=model_name, input=t or "")
        vecs.append(resp.data[0].embedding)
    return np.array(vecs, dtype=np.float32)

# -------------------------
# IO helpers (Parquet from Polars)
# -------------------------
def _read_users_table(path: str) -> pd.DataFrame:
    """
    Read users table produced by the previous Polars step.
    Prefer Parquet (pyarrow) but allow CSV fallback.
    """
    lower = path.lower()
    if lower.endswith(".parquet") or lower.endswith(".pq"):
        # Polars writes standard Parquet: use pyarrow engine for best compatibility
        return pd.read_parquet(path, engine="pyarrow")
    return pd.read_csv(path)

# -------------------------
# Main
# -------------------------
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-users", default="./data/user_profiles.parquet", help="Input user_profiles from previous step")
    ap.add_argument("--backend", choices=["minilm", "openai"], default="minilm", help="Embedding model")
    ap.add_argument("--minilm-model", default="sentence-transformers/all-MiniLM-L6-v2", help="Sentence-Transformers model")
    ap.add_argument("--openai-model", default="text-embedding-3-small", help="OpenAI embedding model")
    ap.add_argument("--out-meta", default="./data/users_meta.csv", help="Output CSV with user meta")
    ap.add_argument("--out-npy", default="./data/users_features.npy", help="Output NPY feature matrix")
    args = ap.parse_args()

    print(cf.bold(cf.green("Begin embedding data...")))
    # Load user profiles (Polars parquet -> pandas DataFrame)
    df = _read_users_table(args.in_users)
    print(cf.bold(cf.green("Loaded users table data")))
    
    # Normalize text
    df["concat_text"] = df["concat_text"].fillna("").map(normalize_text)
    texts = df["concat_text"].tolist()

    # Embeddings
    if args.backend == "minilm":
        E = _embed_minilm(texts, model_name=args.minilm_model)
    else:
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY not set in environment.")
        E = _embed_openai(texts, model_name=args.openai_model)
    
    print(cf.bold(cf.green("Completed embedding data using model")))

    # Numeric/behavior features
    num_cols = [
        "num_reviews", "avg_rating", "std_rating",
        "frac_low", "frac_high", "avg_helpful_votes",
        "pct_verified_purchase", "pct_with_images",
    ]
    X_num = df[num_cols].copy()

    # Enforce numeric types & clean
    for c in num_cols:
        X_num[c] = pd.to_numeric(X_num[c], errors="coerce")
    X_num["avg_helpful_votes"] = X_num["avg_helpful_votes"].fillna(0)

    # Scale
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X_num.values)

    # Final features = [embeddings || numeric]
    X = np.hstack([E, Xs]).astype(np.float32)

    # Save
    meta_cols = ["user_id", "concat_text"] + num_cols
    df[meta_cols].to_csv(args.out_meta, index=False)
    np.save(args.out_npy, X)

    print(cf.bold(cf.green("Saved meta:", args.out_meta)))
    print(cf.bold(cf.green("Saved features:", "{} (shape={})".format(args.out_npy, X.shape))))
