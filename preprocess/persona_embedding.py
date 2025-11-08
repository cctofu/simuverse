import json
import os
import re
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from dotenv import load_dotenv
import time

# ---------------------------
# CONFIG
# ---------------------------
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

INPUT_FILE = "data/Twin-2K-500_with_summaries.json"
OUTPUT_FILE = "data/Twin-2K-500_with_embeddings.json"
EMBEDDING_MODEL = "text-embedding-3-large"
MAX_WORKERS = 5       
SAVE_INTERVAL = 25  

# ---------------------------
# HELPERS
# ---------------------------

def extract_demographics(demo_text: str):
    fields = {}
    if not demo_text:
        return fields
    patterns = {
        "age": r"Age:\s*([^\n]+)",
        "gender": r"Gender:\s*([^\n]+)",
        "region": r"Geographic region:\s*([^\n]+)",
        "income": r"Income:\s*([^\n]+)",
        "education": r"Education level:\s*([^\n]+)",
        "employment": r"Employment status:\s*([^\n]+)",
        "marital_status": r"Marital status:\s*([^\n]+)"
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, demo_text)
        if match:
            fields[key] = match.group(1).strip()
    return fields


def create_embedding_profile(record):
    cs = record.get("consumer_summary", {})
    demo_text = record.get("key_values", {}).get("demographics", "")
    demo = extract_demographics(demo_text)

    demo_summary = ", ".join([
        f"{demo.get('gender', '')}",
        f"{demo.get('age', '')}",
        f"{demo.get('region', '')}",
        f"{demo.get('education', '')}",
        f"{demo.get('employment', '')}",
        f"{demo.get('income', '')}",
        f"{demo.get('marital_status', '')}"
    ])
    demo_summary = " ".join(demo_summary.split())

    # Concise profile text for embedding
    profile_text = (
        f"Demographics: {demo_summary}. "
        f"{cs.get('cognitive_style', '')}. "
        f"{cs.get('decision_motivation', '')}. "
        f"{cs.get('risk_preference', '')}. "
        f"{cs.get('emotional_state', '')}. "
        f"{cs.get('financial_attitude', '')}. "
        f"{cs.get('social_orientation', '')}. "
        f"{cs.get('environmental_values', '')}. "
        f"{cs.get('consumption_pattern', '')}. "
        f"{cs.get('self_concept_and_values', '')}."
    ).replace("\n", " ").strip()

    return profile_text


def generate_embedding_vector(text):
    """Generate embedding vector for given text."""
    if not text.strip():
        return None
    try:
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=text)
        return response.data[0].embedding
    except Exception as e:
        print(f"⚠️ Embedding error: {e}")
        time.sleep(3)
        return None


def process_record(record):
    """Worker function for threading."""
    text = create_embedding_profile(record)
    record["embedding_profile_text"] = text
    record["embedding_vector"] = generate_embedding_vector(text)
    return record


def save_checkpoint(data_dict):
    """Save current progress."""
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(list(data_dict.values()), f, indent=2, ensure_ascii=False)


def main():
    print(f"📥 Loading {INPUT_FILE} ...")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Resume if partial output exists
    existing = {}
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            existing = {r["id"]: r for r in json.load(f)}
        print(f"🔄 Resuming from checkpoint: {len(existing)} completed")

    remaining = [r for r in data if r["id"] not in existing]

    print(f"⚙️ Generating embeddings for {len(remaining)} profiles with {MAX_WORKERS} threads ...")

    completed = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_record, rec) for rec in remaining]
        for future in tqdm(as_completed(futures), total=len(futures)):
            rec = future.result()
            existing[rec["id"]] = rec
            completed += 1

            if completed % SAVE_INTERVAL == 0:
                save_checkpoint(existing)
                print(f"💾 Saved after {completed} embeddings")

    save_checkpoint(existing)
    print(f"✅ All done — total {len(existing)} records processed.")
    print(f"💾 Final file saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
