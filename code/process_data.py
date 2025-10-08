import json
import pandas as pd
from tqdm import tqdm

def build_product_dict(input_path):
    product_dict = {}
    #keep_keys = ["title", "average_rating", "features", "description", "price", "details"]
    keep_keys = ["title", "average_rating"]
    with open(input_path, "r", encoding="utf-8") as infile:
        for line in tqdm(infile):
            line = line.strip()
            data = json.loads(line)
            parent_asin = data.get("parent_asin")
            if parent_asin:
                filtered_data = {k: data.get(k) for k in keep_keys if k in data}
                product_dict[parent_asin] = filtered_data
    return product_dict


COLUMNS = ["rating", "title", "text", "parent_asin", "user_id", "helpful_vote"]

def load_reviews(path, product_dict):
    df = pd.read_json(path, lines=True)
    exist = [c for c in COLUMNS if c in df.columns]
    df = df[exist].copy()

    # Basic cleaning
    df["title"] = df["title"].astype(str)
    df["text"] = df["text"].astype(str)
    df["user_id"] = df["user_id"].astype(str)
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df["helpful_vote"] = pd.to_numeric(df["helpful_vote"], errors="coerce").fillna(0).astype(int)
    meta_df = pd.DataFrame.from_dict(product_dict, orient="index")
    meta_df["parent_asin"] = meta_df.index
    merged_df = df.merge(meta_df, on="parent_asin", how="left")
    merged_df = merged_df.drop(columns=["parent_asin"])
    return merged_df


if __name__ == "__main__":
    METADATA = "./data/meta_All_Beauty.jsonl"
    REVIEW_DATA = "./data/All_Beauty.jsonl"
    OUTPUT_FILE = "./data/product_review.csv"

    print("Begin data cleaning process...")
    product_dict = build_product_dict(METADATA)
    print("Completed product dictionary construction")
    df = load_reviews(REVIEW_DATA, product_dict)
    print("Completed dataframe for reviews")
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
    print(f"Saved merged product reviews to {OUTPUT_FILE} with {len(df)} rows.")
    print("Complete!")
