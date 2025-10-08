import argparse
import html
import re
from typing import Optional, List
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from sklearn.feature_extraction.text import TfidfVectorizer

import numpy as np
import pandas as pd

# ----------------------------
# Text utilities
# ----------------------------
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")

def strip_html(s: str) -> str:
    if not isinstance(s, str):
        return ""
    # Unescape HTML entities and remove tags
    s = html.unescape(s)
    s = _TAG_RE.sub(" ", s)
    s = _WS_RE.sub(" ", s).strip()
    return s

def simple_tokenize(s: str) -> List[str]:
    # Very lightweight tokenizer: split on non-letters/digits
    if not isinstance(s, str):
        return []
    return re.findall(r"[A-Za-z0-9]+", s.lower())

# ----------------------------
# Sentiment
# ----------------------------
class SentimentScorer:
    def __init__(self):
        # initialize analyzer and mark class as enabled
        self.enabled = True
        self.analyzer = SentimentIntensityAnalyzer()

    def score(self, text: str) -> Optional[float]:
        if not self.enabled:
            return np.nan
        if not isinstance(text, str) or not text.strip():
            return np.nan
        # compound ∈ [-1, 1]: negative → −1, neutral → 0, positive → +1
        return float(self.analyzer.polarity_scores(text)["compound"])
# ----------------------------
# Core pipeline
# ----------------------------
def clean_reviews(df: pd.DataFrame, min_tokens: int = 5) -> pd.DataFrame:
    # Keep only expected columns if present
    expected = ["user_id", "text", "rating", "helpful_vote", "product_title", "product_average_rating"]
    cols = [c for c in expected if c in df.columns]
    df = df[cols].copy()

    # Types & basic normalization
    for c in ["user_id", "text", "product_title"]:
        if c in df.columns:
            df[c] = df[c].astype(str)

    if "rating" in df.columns:
        df["rating"] = pd.to_numeric(df["rating"], errors="coerce")

    if "helpful_vote" in df.columns:
        df["helpful_vote"] = pd.to_numeric(df["helpful_vote"], errors="coerce").fillna(0).astype(int)

    if "product_average_rating" in df.columns:
        df["product_average_rating"] = pd.to_numeric(df["product_average_rating"], errors="coerce")

    # Strip HTML / whitespace
    if "text" in df.columns:
        df["text"] = df["text"].map(strip_html)

    # Drop empty/very short reviews
    if "text" in df.columns:
        df["review_len_tokens"] = df["text"].map(lambda s: len(simple_tokenize(s)))
        df = df[df["review_len_tokens"] >= int(min_tokens)]

    # Remove exact dupes on (user_id, text) to reduce spam
    if set(["user_id", "text"]).issubset(df.columns):
        df = df.drop_duplicates(subset=["user_id", "text"])

    # Clip impossible values
    if "rating" in df.columns:
        df = df[(df["rating"].isna()) | ((df["rating"] >= 1.0) & (df["rating"] <= 5.0))]

    # Feature: helpful_vote_log
    if "helpful_vote" in df.columns:
        df["helpful_vote_log"] = np.log1p(df["helpful_vote"].clip(lower=0))

    return df.reset_index(drop=True)


def aggregate_user_personas(df):
    # Build aggregation dictionary
    agg = {
        "rating": ["mean", "median", "std", "count"],
        "helpful_vote_log": ["mean", "median"],
        "review_len_tokens": ["mean", "median"],
        "product_average_rating": ["mean", "median"],
        "sentiment": ["mean", "median"]
    }
    grouped = df.groupby("user_id").agg(agg)

    # Flatten MultiIndex columns
    grouped.columns = ["_".join([c for c in col if c]).strip("_") for col in grouped.columns.values]
    grouped = grouped.rename(columns={
        "rating_mean": "avg_rating",
        "rating_median": "median_rating",
        "rating_std": "rating_std",
        "rating_count": "n_reviews",
        "helpful_vote_log_mean": "avg_helpful_vote_log",
        "helpful_vote_log_median": "median_helpful_vote_log",
        "review_len_tokens_mean": "avg_review_len_tokens",
        "review_len_tokens_median": "median_review_len_tokens",
        "product_average_rating_mean": "avg_product_average_rating",
        "product_average_rating_median": "median_product_average_rating",
        "sentiment_mean": "avg_sentiment",
        "sentiment_median": "median_sentiment",
    })

    # Order columns sensibly
    ordered = [
        "n_reviews",
        "avg_rating", "median_rating", "rating_std",
        "avg_helpful_vote_log", "median_helpful_vote_log",
        "avg_review_len_tokens", "median_review_len_tokens",
        "avg_product_average_rating", "median_product_average_rating",
        "avg_sentiment", "median_sentiment"
    ]
    # Keep only present
    ordered = [c for c in ordered if c in grouped.columns]
    grouped = grouped[ordered].reset_index()
    return grouped

# ----------------------------
# CLI
# ----------------------------
def parse_args():
    p = argparse.ArgumentParser(description="Build user-level audience personas from reviews CSV.")
    p.add_argument("--out_personas", default="./data/user_personas.csv", help="Output CSV for user personas.")
    p.add_argument("--min_tokens", type=int, default=5, help="Minimum token length to keep a review.")
    return p.parse_args()

if __name__ == "__main__":
    args = parse_args()
    print("Begin user building process...")
    df = pd.read_csv('./data/product_review.csv')
    df_clean = clean_reviews(df, min_tokens=args.min_tokens)
    print("Cleaned dataframe")
    scorer = SentimentScorer()
    df["sentiment"] = df["text"].map(scorer.score)
    print("Added sentiment to dataframe")
    personas = aggregate_user_personas(df_clean)
    print("Aggregated user personas")
    personas.to_csv(args.out_personas, index=False, encoding="utf-8")
    print(f"Personas saved: {args.out_personas}  (users={len(personas)})")
    print("Complete!")
