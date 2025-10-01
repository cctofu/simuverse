#!/usr/bin/env python3
import json
import re
import hashlib
import argparse
from pathlib import Path

import pandas as pd
import numpy as np
from tqdm import tqdm


# ---------------------------
# Step 1: Load & clean reviews
# ---------------------------
def normalize_text(text: str) -> str:
    """Lowercase, collapse whitespace, strip."""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def load_clean_dedup_jsonl(jsonl_path: str, min_length: int = 15) -> pd.DataFrame:
    """
    Load reviews from JSONL, build clean_text = title + text, drop very short texts,
    and de-duplicate near-identical texts by hash.

    Returns a DataFrame with one row per cleaned, deduplicated review.
    """
    rows = []
    seen_hashes = set()

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in tqdm(f, desc="Loading reviews"):
            if not line.strip():
                continue
            d = json.loads(line)

            title = str(d.get("title", "")).strip()
            body = str(d.get("text", "")).strip()
            clean_text = normalize_text(f"{title} {body}".strip())

            # Drop too-short reviews
            if len(clean_text) < min_length:
                continue

            # De-duplicate by text hash
            text_hash = hashlib.md5(clean_text.encode("utf-8")).hexdigest()
            if text_hash in seen_hashes:
                continue
            seen_hashes.add(text_hash)

            rows.append({
                "user_id": d.get("user_id"),
                "asin": d.get("asin"),
                "parent_asin": d.get("parent_asin"),
                "rating": d.get("rating"),
                "helpful_votes": d.get("helpful_votes", 0),
                "verified_purchase": bool(d.get("verified_purchase", False)),
                "images": d.get("images", []),
                "sort_timestamp": d.get("sort_timestamp"),
                "clean_text": clean_text
            })

    df = pd.DataFrame(rows)
    # Ensure types are sane
    if not df.empty:
        df["helpful_votes"] = pd.to_numeric(df["helpful_votes"], errors="coerce").fillna(0).astype(int)
        df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
        # Optional: has_images convenience flag
        df["has_images"] = df["images"].apply(lambda x: int(bool(x)))
    return df


# ------------------------------------------
# Step 2: Aggregate cleaned reviews per user
# ------------------------------------------
def aggregate_to_users(reviews_df: pd.DataFrame, max_reviews_per_user: int = 20) -> pd.DataFrame:
    """
    Aggregate review-level data into user-level profiles.
    Concatenates up to N reviews' clean_text and computes behavioral features.
    """
    if reviews_df.empty:
        return pd.DataFrame(columns=[
            "user_id", "num_reviews", "avg_rating", "std_rating",
            "frac_low", "frac_high", "avg_helpful_votes",
            "pct_verified_purchase", "pct_with_images", "concat_text"
        ])

    user_rows = []
    # Sort once for deterministic concatenation
    reviews_df = reviews_df.sort_values("sort_timestamp")

    for user_id, g in reviews_df.groupby("user_id", dropna=False):
        texts = g["clean_text"].tolist()
        concat_text = " ".join(texts[:max_reviews_per_user])

        num_reviews = len(g)
        ratings = g["rating"].astype(float)
        avg_rating = float(ratings.mean())
        std_rating = float(ratings.std(ddof=0)) if num_reviews > 1 else 0.0
        frac_low = float((ratings <= 2).mean())
        frac_high = float((ratings >= 4).mean())

        helpful = g["helpful_votes"].clip(0, 200)  # cap outliers
        avg_helpful = float(helpful.mean())

        pct_verified = float(g["verified_purchase"].astype(int).mean())
        # If has_images is present, use it; else compute from images list
        if "has_images" in g.columns:
            pct_with_images = float(g["has_images"].astype(int).mean())
        else:
            pct_with_images = float(g["images"].apply(lambda x: int(bool(x))).mean())

        user_rows.append({
            "user_id": user_id,
            "num_reviews": num_reviews,
            "avg_rating": avg_rating,
            "std_rating": std_rating,
            "frac_low": frac_low,
            "frac_high": frac_high,
            "avg_helpful_votes": avg_helpful,
            "pct_verified_purchase": pct_verified,
            "pct_with_images": pct_with_images,
            "concat_text": concat_text
        })

    return pd.DataFrame(user_rows)


# --------------
# Main / CLI
# --------------
def parse_args():
    p = argparse.ArgumentParser(
        description="Load/clean Amazon reviews from JSONL and aggregate to user profiles."
    )
    p.add_argument("input_jsonl", help="Path to input .jsonl file")
    p.add_argument("--min-length", type=int, default=15,
                   help="Minimum length of clean_text to keep (default: 15)")
    p.add_argument("--max-reviews-per-user", type=int, default=20,
                   help="Max number of reviews to concatenate per user (default: 20)")
    p.add_argument("--save-cleaned", type=str, default="",
                   help="Optional path to save cleaned reviews CSV (default: do not save)")
    p.add_argument("--out-users", type=str, default="user_profiles.csv",
                   help="Output CSV for aggregated user profiles (default: user_profiles.csv)")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    input_path = Path(args.input_jsonl)

    # Step 1: load + clean + dedup
    reviews_df = load_clean_dedup_jsonl(str(input_path), min_length=args.min_length)
    print(f"\nCleaned & deduplicated reviews: {len(reviews_df):,}")

    if args.save_cleaned:
        out_clean = Path(args.save_cleaned)
        reviews_df.to_csv(out_clean, index=False)
        print(f"Saved cleaned reviews to: {out_clean.resolve()}")

    # Step 2: aggregate per user
    users_df = aggregate_to_users(reviews_df, max_reviews_per_user=args.max_reviews_per_user)
    print(f"Aggregated users: {len(users_df):,}")

    out_users = Path(args.out_users)
    users_df.to_csv(out_users, index=False)
    print(f"Saved user profiles to: {out_users.resolve()}")