from datasets import load_dataset
import json
import re
import argparse
from tqdm import tqdm

# ---------------------------
# CONFIG
# ---------------------------
DATASET_NAME = "LLM-Digital-Twin/Twin-2K-500"
CONFIG_NAME = "full_persona"


# ---------------------------
# HELPERS
# ---------------------------
PATTERN = re.compile(
    r"The person(?:'s| is)?\s*(.*?)\s*(?:is|are)\s+the\s+following[:：]?\s*(.*)",
    re.IGNORECASE | re.DOTALL
)

def split_into_paragraphs(text: str):
    """Split long persona text into chunks by paragraph breaks."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    return paragraphs


def extract_key_value(chunk: str):
    """Extract key and value from text chunks like:
       'The person's Big 5 scores are the following: score_extraversion = 3.5 ...'
    """
    match = PATTERN.search(chunk)
    if match:
        key = match.group(1).strip()
        value = match.group(2).strip()
        key = key.replace(".", "").replace("’", "'")
        return key, value
    return None, None


# ---------------------------
# MAIN PIPELINE
# ---------------------------
def main():
    parser = argparse.ArgumentParser(description="Download and process persona dataset")
    parser.add_argument(
        "-o", "--output",
        type=str,
        required=True,
        help="Output file path (required)"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=DATASET_NAME,
        help=f"Dataset name (default: {DATASET_NAME})"
    )
    parser.add_argument(
        "--config",
        type=str,
        default=CONFIG_NAME,
        help=f"Config name (default: {CONFIG_NAME})"
    )
    args = parser.parse_args()

    output_file = args.output
    dataset_name = args.dataset
    config_name = args.config

    print(f"📥 Downloading dataset: {dataset_name} ({config_name}) ...")
    ds = load_dataset(dataset_name, config_name)

    # Combine all splits into one list
    if isinstance(ds, dict):
        records = []
        for split_name, split_data in ds.items():
            print(f"🧩 Processing split '{split_name}' with {len(split_data)} records")
            records.extend(split_data)
    else:
        records = list(ds)

    processed = []
    total_pairs = 0

    for i, rec in enumerate(tqdm(records, desc="Processing personas")):
        user_id = rec.get("user_id", f"user_{i:06d}")

        # Use persona_summary if available, else persona_text, else fallback
        raw_text = (
            rec.get("persona_summary")
            or rec.get("persona_text")
            or rec.get("text")
            or json.dumps(rec, ensure_ascii=False)
        )

        chunks = split_into_paragraphs(raw_text)
        if not chunks:
            continue

        # 1️⃣ Remove first chunk
        chunks = chunks[1:] if len(chunks) > 1 else chunks

        # 2️⃣ Extract last chunk → qualitative questions
        qualitative = None
        if len(chunks) > 1:
            qualitative = chunks[-1]
            chunks = chunks[:-1]

        # 3️⃣ Parse remaining chunks into key–value pairs
        key_values = {}
        for ch in chunks:
            key, value = extract_key_value(ch)
            if key and value:
                key_values[key] = value
                total_pairs += 1

        processed.append({
            "id": user_id,
            "key_values": key_values,
            "qualitative_questions": qualitative
        })

    print(f"🧩 Extracted {total_pairs} key–value pairs across {len(processed)} users")
    print(f"💾 Writing structured personas to {output_file} ...")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(processed, f, ensure_ascii=False, indent=2)

    print(f"✅ Done! Saved structured persona dataset to {output_file}")


if __name__ == "__main__":
    main()
