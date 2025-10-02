import argparse
from pathlib import Path
import polars as pl
import colorful as cf


def normalized_text_expr():
    """Polars expression to normalize review text (lowercase, collapse spaces, strip)."""
    return (
        (pl.coalesce([pl.col("title"), pl.lit("")]) + pl.lit(" ") + pl.coalesce([pl.col("text"), pl.lit("")]))
        .str.to_lowercase()
        .str.replace_all(r"\s+", " ")
        .str.strip_chars()
        .alias("clean_text")
    )


def process_reviews(jsonl_path: str, min_length: int = 15, max_reviews_per_user: int = 20) -> pl.DataFrame:
    """
    Stream reviews from JSONL, clean/dedup, and directly aggregate into user profiles.
    Returns a Polars DataFrame with one row per user.
    """

    # 1) Lazily scan the JSONL (NDJSON) file
    lf = pl.scan_ndjson(jsonl_path)

    # 2) Clean + select relevant columns
    lf = (
        lf.select(
            pl.col("user_id"),
            pl.col("rating").cast(pl.Float32),
            pl.col("helpful_vote").cast(pl.Int32).fill_null(0),
            pl.col("verified_purchase").fill_null(False).cast(pl.Int8),
            (pl.col("images").list.len().fill_null(0) > 0).cast(pl.Int8).alias("has_images"),
            pl.col("timestamp"),
            normalized_text_expr(),
        )
        .filter(pl.col("clean_text").str.len_chars() >= min_length)
        .unique(subset=["clean_text"])
    )

    # 3) Aggregate per user
    lf_users = (
        lf.group_by("user_id")
        .agg(
            pl.len().alias("num_reviews"),
            pl.col("rating").mean().alias("avg_rating"),
            pl.col("rating").std().fill_null(0).alias("std_rating"),
            (pl.col("rating") <= 2).mean().alias("frac_low"),
            (pl.col("rating") >= 4).mean().alias("frac_high"),
            pl.col("helpful_vote").clip(200).mean().alias("avg_helpful_votes"),
            pl.col("verified_purchase").mean().alias("pct_verified_purchase"),
            pl.col("has_images").mean().alias("pct_with_images"),
            pl.col("clean_text").alias("texts"),
        )
        .with_columns(
            pl.col("texts").list.slice(0, max_reviews_per_user).list.join(" ").alias("concat_text")
        )
        .drop("texts")
    )

    return lf_users.collect(engine="streaming")


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("input_jsonl", help="Path to input .jsonl file")
    p.add_argument("--min-length", type=int, default=15)
    p.add_argument("--max-reviews-per-user", type=int, default=20)
    p.add_argument("--out-users", type=str, default=f"./data/user_profiles.parquet")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    out_path = Path(args.out_users).with_suffix(".parquet")

    print(cf.bold(cf.green('Begin processing data...')))
    users_df = process_reviews(
        args.input_jsonl,
        min_length=args.min_length,
        max_reviews_per_user=args.max_reviews_per_user,
    )
    print(cf.bold(cf.green(f"Aggregated users: {users_df.height:,}")))
    users_df.write_parquet(out_path, compression="snappy")
    print(cf.bold(cf.green(f"Saved user profiles to: {out_path.resolve()}")))
