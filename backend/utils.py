import json
import os
import pandas as pd
from openai import OpenAI
from typing import Dict, Any, List
import time
import random
import numpy as np
from tqdm import tqdm

from prompts import (
    PURCHASE_DECISION_SYSTEM_PROMPT,
    PERSONA_GENERATION_SYSTEM_PROMPT,
    PERSONA_CLASSIFICATION_SYSTEM_PROMPT,
    RELEVANT_PERSONA_SELECTION_SYSTEM_PROMPT,
    get_relevant_personality_prompt,
    get_persona_generation_prompt,
    get_persona_classification_prompt
)
from dotenv import load_dotenv

# ============================================================================
# DATA LOADING
# ============================================================================
DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "Twin-2K-500_full_full.parquet")

print(f"📦 Loading persona data from {DATA_PATH}...")
try:
    PERSONA_DF = pd.read_parquet(DATA_PATH)
    print(f"✅ Loaded {len(PERSONA_DF)} personas successfully!")
except Exception as e:
    print(f"❌ Error loading data: {e}")
    PERSONA_DF = pd.DataFrame()

# ============================================================================
# OPENAI CONFIGURATION
# ============================================================================
load_dotenv()

def get_openai_client():
    """Get OpenAI client instance."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    return OpenAI(api_key=api_key)
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

# ============================================================================
# UTILS
# ============================================================================
def invoke_llm_model(prompt: str, system_prompt: str, max_tokens: int = 512) -> str:
    """Invoke OpenAI GPT model."""
    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ OpenAI invocation error: {e}")
        return ""


def get_relevant_personality():
    with open("data/personas.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return [item["name"] for item in data]


def get_persona_data():
    df = pd.read_parquet("data/Twin-2K-500_full_full.parquet")
    return df


# ============================================================================
# STEP 1: Relevant Persona Generation
# ============================================================================
def generate_relevant_personas(product_description: str) -> List[str]:
    system_prompt = RELEVANT_PERSONA_SELECTION_SYSTEM_PROMPT
    attributes = get_relevant_personality()
    user_prompt = get_relevant_personality_prompt(product_description, attributes)
    response_text = invoke_llm_model(user_prompt, system_prompt, max_tokens=200)
    try:
        response_text = (response_text or "").strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        parsed = json.loads(response_text)
        if isinstance(parsed, list) and all(isinstance(x, str) for x in parsed):
            return parsed
    except Exception as e:
        print(f"⚠️ Trait selection parse error: {e}. Response: {response_text}")


# ============================================================================
# STEP 2: Generate Product Persona 
# ============================================================================
def generate_product_personas(product_description: str) -> Dict[str, Any]:
    """
    Ask the model to generate 5 distinct consumer personality profiles
    that would likely purchase or be interested in this product.
    Returns a dict with 'personas', 'age_ranges', and 'gender'.
    """
    system_prompt = PERSONA_GENERATION_SYSTEM_PROMPT
    # Updated user prompt:
    user_prompt = get_persona_generation_prompt(product_description, num_personas=5)

    # Call the model
    response_text = invoke_llm_model(user_prompt, system_prompt, max_tokens=200)

    # Parse model output
    try:
        response_text = (response_text or "").strip()

        # Remove markdown code blocks
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]

        # Try to find JSON object in the response
        # Look for the first { and last } to extract just the JSON
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}')

        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_str = response_text[start_idx:end_idx+1]
            parsed = json.loads(json_str)

            # Validate structure
            if isinstance(parsed, dict):
                personas = parsed.get("personas", [])
                age_ranges = parsed.get("age_ranges", [])
                gender = parsed.get("gender", "Both")

                # Ensure personas is a list of strings
                if isinstance(personas, list) and all(isinstance(x, str) for x in personas):
                    return {
                        "personas": personas,
                        "age_ranges": age_ranges,
                        "gender": gender
                    }

        print(f"⚠️ Unexpected format. Model returned: {response_text}")
        return {"personas": [], "age_ranges": [], "gender": "Both"}

    except Exception as e:
        print(f"⚠️ Persona generation parse error: {e}. Response: {response_text}")
        return {"personas": [], "age_ranges": [], "gender": "Both"}


# ============================================================================
# STEP 3: Find top 100 personas who is most relevant
# ============================================================================
def find_top_personas(generated_personas, top_k=10):
    import pandas as pd, numpy as np, json

    PERSONA_LABEL_PATH = "data/personas.json"
    PARQUET_PATH = "data/Twin-2K-500_full_full.parquet"

    with open(PERSONA_LABEL_PATH, "r", encoding="utf-8") as f:
        persona_data = json.load(f)
    persona_labels = [p["name"] for p in persona_data]
    num_labels = len(persona_labels)

    query_vec = np.array([1 if label in generated_personas else 0 for label in persona_labels], dtype=int)

    df = pd.read_parquet(PARQUET_PATH)

    # If the file has a single "vector" column:
    if "vector" in df.columns:
        # Expand the vector column into 100 columns
        vectors = np.vstack(df["vector"].to_numpy())
        matrix = vectors
    else:
        # Otherwise assume each persona label is a column
        matrix = df[persona_labels].to_numpy(dtype=int)

    similarities = matrix @ query_vec
    df["similarity"] = similarities

    return df.sort_values("similarity", ascending=False).head(top_k)[["pid", "similarity"]]

# ============================================================================
# STEP 4: Purchase Decisions
# ============================================================================

def analyze_purchase_decisions(product_description: str, age_ranges: List[str] = None, gender: str = "Both") -> Dict[str, Any]:
    system_prompt = PURCHASE_DECISION_SYSTEM_PROMPT

    results = {"yes": 0, "no": 0, "unknown": 0, "details": []}

    BASE_DELAY = 1.0        # seconds between normal calls
    MAX_RETRIES = 5         # for throttled calls
    BACKOFF_FACTOR = 2.0    # exponential multiplier

    subset_df = PERSONA_DF.head(50)
    total_personas = len(subset_df)
    print(f"🔍 Beginning purchase decision analysis for {total_personas} personas (test mode, rate-limited)...")

    # for i, row in tqdm(PERSONA_DF.iterrows()):
    for i, row in tqdm(subset_df.iterrows(), total=total_personas, desc="Analyzing personas"):
        persona_summary = row.get("persona_summary", "")
        if not persona_summary:
            continue

        user_prompt = f"<PROFILE>\n{persona_summary}\n</PROFILE>\n\n<PRODUCT>\n{product_description}\n</PRODUCT>"

        # retry loop for throttling or transient network errors
        for attempt in range(MAX_RETRIES):
            try:
                response = invoke_llm_model(user_prompt, system_prompt, max_tokens=10).lower()
                break  # success → exit retry loop
            except Exception as e:
                error_msg = str(e).lower()
                # Check for rate limit errors
                if "rate" in error_msg or "quota" in error_msg or "429" in error_msg:
                    wait_time = (BACKOFF_FACTOR ** attempt) + random.uniform(0.1, 0.5)
                    print(f"⚠️ Rate limited (attempt {attempt+1}/{MAX_RETRIES}). Sleeping {wait_time:.1f}s...")
                    time.sleep(wait_time)
                else:
                    print(f"❌ Error on persona {i}: {e}")
                    response = "unknown"
                    break

        # normalize model output
        if "yes" in response:
            decision = "yes"
            results["yes"] += 1
        elif "no" in response:
            decision = "no"
            results["no"] += 1
        else:
            decision = "unknown"
            results["unknown"] += 1

        results["details"].append({
            "persona_id": row.get("pid", i),
            "decision": decision,
            "persona_summary": persona_summary,
            "age": row.get("Age", None)
        })

        # polite delay between calls to stay under QPS limits
        delay = BASE_DELAY + random.uniform(0.1, 0.5)
        time.sleep(delay)

        # progress update every 50 personas
        if (i + 1) % 50 == 0:
            print(f"✅ Processed {i + 1}/{total_personas} personas so far...")

    # summary stats
    total = results["yes"] + results["no"] + results["unknown"]
    results["total_evaluated"] = total
    results["purchase_rate"] = round(results["yes"] / total, 2) if total > 0 else 0.0

    print(f"🏁 Completed {total} personas — {results['yes']} yes / {results['no']} no / {results['unknown']} unknown.")
    return results

# ============================================================================
# STEP 5: Classify "Yes" Personas
# ============================================================================
def classify_yes_personas(
    yes_personas: List[Dict[str, Any]],
    generated_titles: List[str]
) -> List[Dict[str, Any]]:
    """
    Classify each 'yes' persona into one of the generated archetype titles
    using both their summary and structured attributes.
    """
    system_prompt = PERSONA_CLASSIFICATION_SYSTEM_PROMPT
    classified = []

    for p in yes_personas:
        persona_summary = p.get("persona_summary", "")
        persona_attributes = p.get("persona_attributes", {})  # optional structured data

        # Build prompt using the helper function
        user_prompt = get_persona_classification_prompt(
            generated_titles,
            persona_summary,
            persona_attributes
        )

        # Call model
        response = invoke_llm_model(user_prompt, system_prompt, max_tokens=50)
        match = (response or "").strip().strip('"').strip("'")

        # Normalize to 'Other' if not an exact match
        if match not in generated_titles:
            match = "Other"

        classified.append({
            "persona_id": p.get("persona_id"),
            "assigned_archetype": match,
            "persona_summary": persona_summary,
            "persona_attributes": persona_attributes
        })

    return classified

# ============================================================================
# STEP 6: Generate Persona Insights
# ============================================================================
def generate_persona_insights(
    product_description: str,
    product_persona_name: str,
    persona_summary: str
) -> Dict[str, str]:
    """
    Given a product description, product persona name, and persona summary,
    prompt the model to answer three questions as the persona in 1 sentence each:
    1. How likely are you to buy this product?
    2. How relevant is this product to you?
    3. What is your purchase intent for this product?

    Returns a dictionary with the three answers.
    """
    system_prompt = """You are role-playing as the persona described. Answer each question in exactly 1 sentence from the perspective of this persona. Be specific and authentic to the persona's characteristics."""

    user_prompt = f"""<PERSONA_TYPE>
{product_persona_name}
</PERSONA_TYPE>

<PERSONA_SUMMARY>
{persona_summary}
</PERSONA_SUMMARY>

<PRODUCT>
{product_description}
</PRODUCT>

Based on the persona above, answer the following three questions in exactly 1 sentence each:

1. How likely are you to buy this {product_description}?
2. How relevant is this {product_description} to you?
3. What is your purchase intent for this {product_description}?

Format your response as:
LIKELIHOOD: [your 1 sentence answer]
RELEVANCE: [your 1 sentence answer]
INTENT: [your 1 sentence answer]"""

    try:
        response = invoke_llm_model(user_prompt, system_prompt, max_tokens=300)

        # Parse the response to extract the three answers
        answers = {
            "likelihood": "",
            "relevance": "",
            "intent": ""
        }

        lines = response.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith("LIKELIHOOD:"):
                answers["likelihood"] = line.replace("LIKELIHOOD:", "").strip()
            elif line.startswith("RELEVANCE:"):
                answers["relevance"] = line.replace("RELEVANCE:", "").strip()
            elif line.startswith("INTENT:"):
                answers["intent"] = line.replace("INTENT:", "").strip()

        return answers

    except Exception as e:
        print(f"❌ Error generating insights: {e}")
        return {
            "likelihood": "Error generating response",
            "relevance": "Error generating response",
            "intent": "Error generating response"
        }
