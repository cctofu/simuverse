import json
import os
import sys
import time
import argparse
from tqdm import tqdm
from openai import OpenAI
from dotenv import load_dotenv
import numpy as np

# ---------------------------
# CONFIG
# ---------------------------
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OPENAI_API_KEY

load_dotenv()
client = OpenAI(api_key=OPENAI_API_KEY)


# ---------------------------
# HELPERS
# ---------------------------

def map_age_group(demo_text):
    """Map free-text ages to fixed 4 bins."""
    if not demo_text:
        return "Unknown"
    text = demo_text.lower()
    if any(k in text for k in ["18", "20", "29"]):
        return "18-29"
    elif any(k in text for k in ["30", "40", "49"]):
        return "30-49"
    elif any(k in text for k in ["50", "55", "60", "64"]):
        return "50-64"
    elif "65" in text or "70" in text or "80" in text or "senior" in text:
        return "65+"
    return "Unknown"


def create_cluster_text(record):
    """Extract relevant fields to form text for embedding."""
    cs = record.get("consumer_summary", {})
    return " ".join([
        cs.get("demographic_overview", ""),
        cs.get("consumption_pattern", ""),
        cs.get("financial_attitude", ""),
        cs.get("environmental_values", "")
    ]).strip()


def generate_embedding_vector(text):
    """Generate embedding vector for the given text."""
    if not text.strip():
        return None
    try:
        response = client.embeddings.create(model="text-embedding-3-small", input=text)
        return response.data[0].embedding
    except Exception as e:
        print(f"⚠️ Embedding error: {e}")
        time.sleep(3)
        return None


# ---------------------------
# MAIN PIPELINE
# ---------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate cluster embeddings for persona dataset")
    parser.add_argument(
        "-i", "--input",
        type=str,
        required=True,
        help="Input file path (required)"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        required=True,
        help="Output file path (required)"
    )
    args = parser.parse_args()

    input_file = args.input
    output_file = args.output

    print(f"📥 Loading {input_file} ...")
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    records = []
    embeddings = []

    print(f"⚙️ Generating embeddings for {len(data)} records ...")
    for rec in tqdm(data):
        text = create_cluster_text(rec)
        emb = generate_embedding_vector(text)
        if emb is not None:
            rec["cluster_embedding_vector"] = emb
            embeddings.append(emb)

    # ---------------------------
    # Clean and normalize embeddings
    # ---------------------------
    print("🧹 Cleaning and normalizing embeddings ...")
    X = np.array(embeddings, dtype=np.float32)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    X = np.clip(X, -1e6, 1e6)
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    valid_mask = norms[:, 0] > 0
    X = X[valid_mask] / norms[valid_mask]
    records = [rec for i, rec in enumerate(records) if valid_mask[i]]

    # ---------------------------
    # Save processed output
    # ---------------------------
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    print(f"✅ Done! {len(records)} records saved to {output_file}")


if __name__ == "__main__":
    main()
