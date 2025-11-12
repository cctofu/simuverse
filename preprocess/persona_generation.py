import json
import os
import re
import argparse
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MAX_WORKERS, SAVE_INTERVAL, SUMMARY_MODEL, OPENAI_API_KEY

# ---------------------------
# CONFIG
# ---------------------------
client = OpenAI(api_key=OPENAI_API_KEY)
 
# ---------------------------
# SYSTEM PROMPT
# ---------------------------

CONSUMER_SUMMARY_SYSTEM = """You are a research psychologist trained in cognitive science and behavioral economics.
You will receive:
1. A detailed record of a person's psychological, behavioral, and demographic scores.
2. Their qualitative self-descriptions about who they aspire to be, ought to be, and actually are.

Your task: write a truthful, grounded, and interpretable summary of this person’s consumer-relevant traits.
Incorporate the qualitative context to better describe motivation, values, and social tendencies.

Base your reasoning ONLY on provided data (scores and qualitative text). Do not speculate.
Reflect how personality, cognition, emotion, social orientation, and self-concept influence consumer behavior.

Output strictly in JSON format:
{
  "demographic_overview": "...",
  "cognitive_style": "...",
  "decision_motivation": "...",
  "social_orientation": "...",
  "risk_preference": "...",
  "emotional_state": "...",
  "financial_attitude": "...",
  "environmental_values": "...",
  "consumption_pattern": "...",
  "creativity_openness": "...",
  "self_concept_and_values": "...",
  "summary_overview": "1–2 sentences summarizing this person's likely consumer profile."
}
"""

# ---------------------------
# HELPERS
# ---------------------------

def clean_json_output(text: str):
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text)
    text = re.sub(r"```$", "", text)
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        text = match.group(0)
    return text.strip()

def safe_parse_gpt_json(response_text: str):
    try:
        cleaned = clean_json_output(response_text)
        return json.loads(cleaned)
    except Exception as e:
        return {"error": str(e), "raw_output": response_text}

def generate_consumer_summary(record):
    persona_text = json.dumps(record["key_values"], indent=2)
    qualitative = record.get("qualitative_questions", "")
    user_prompt = f"""
Below is a detailed record of one person's psychological and behavioral scores,
along with their self-concept descriptions.

DATA:
{persona_text}

QUALITATIVE SELF-CONCEPT:
{qualitative}
"""
    try:
        response = client.chat.completions.create(
            model=SUMMARY_MODEL,
            messages=[
                {"role": "system", "content": CONSUMER_SUMMARY_SYSTEM},
                {"role": "user", "content": user_prompt}
            ]
        )
        result = safe_parse_gpt_json(response.choices[0].message.content)
    except Exception as e:
        result = {"error": str(e)}
    record["consumer_summary"] = result
    return record

# ---------------------------
# PARALLEL PIPELINE
# ---------------------------

def save_progress(data, output_file):
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def main():
    parser = argparse.ArgumentParser(description="Generate consumer summaries for persona dataset")
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

    # Load existing partial results if resuming
    if os.path.exists(output_file):
        print("🔄 Resuming from existing file...")
        with open(output_file, "r", encoding="utf-8") as f:
            existing = {r["id"]: r for r in json.load(f)}
    else:
        existing = {}

    # Filter unfinished records
    remaining = [r for r in data if r["id"] not in existing or "consumer_summary" not in existing[r["id"]]]

    print(f"⚙️ Processing {len(remaining)} remaining profiles with {MAX_WORKERS} threads ...")
    completed = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(generate_consumer_summary, r) for r in remaining]
        for future in tqdm(as_completed(futures), total=len(futures)):
            rec = future.result()
            existing[rec["id"]] = rec
            completed += 1

            if completed % SAVE_INTERVAL == 0:
                save_progress(list(existing.values()), output_file)
                print(f"💾 Saved checkpoint after {completed} profiles")

    # Final save
    save_progress(list(existing.values()), output_file)
    print(f"✅ Finished processing {completed} profiles.")
    print(f"💾 Results saved to {output_file}")

if __name__ == "__main__":
    main()
