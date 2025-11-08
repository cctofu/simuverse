import json
import os
from typing import List, Dict, Any
from openai import OpenAI
import numpy as np
from config import EMBEDDING_MODEL, OPENAI_API_KEY, TOP_K, DATABASE_PATH

def generate_structured_query(client: OpenAI, product_description: str) -> str:
    """
    Use GPT to rewrite the product description into a structured
    persona-like summary for embedding. This mirrors the style of
    consumer_summary / embedding_profile_text entries.
    """
    system_prompt = (
        "You are a market psychologist. Rewrite the given product description "
        "into a structured, persona-compatible summary emphasizing how the "
        "product aligns with consumer values, motivations, risk attitudes, "
        "emotional appeal, and lifestyle context. Keep it short (≈5–7 sentences)."
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",  # lightweight reasoning model
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": product_description}
        ],
        temperature=0.4,
    )
    return response.choices[0].message.content.strip()

def load_personas(db_path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database file not found: {db_path}")
    with open(db_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Database JSON should be a list of persona objects.")
    return data


def l2_normalize(v: List[float]) -> List[float]:
    arr = np.asarray(v, dtype="float32")
    norm = np.linalg.norm(arr)
    return (arr / norm).tolist() if norm > 0 else arr.tolist()


def cosine_sim(a: List[float], b: List[float]) -> float:
    va = np.asarray(a, dtype="float32")
    vb = np.asarray(b, dtype="float32")
    denom = (np.linalg.norm(va) * np.linalg.norm(vb))
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


def ensure_persona_vectors(personas: List[Dict[str, Any]]) -> None:
    missing = [p.get("id") for p in personas if not p.get("embedding_vector")]
    if missing:
        raise ValueError(
            f"The following personas are missing 'embedding_vector': {missing[:10]}"
            + (" ..." if len(missing) > 10 else "")
        )
    # Normalize all vectors to be safe
    for p in personas:
        p["embedding_vector"] = l2_normalize(p["embedding_vector"])


def embed_query(client: OpenAI, text: str) -> List[float]:
    resp = client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    vec = resp.data[0].embedding
    return l2_normalize(vec)


def rank_personas(query_vec: List[float], personas: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
    scored: List[Dict[str, Any]] = []
    for p in personas:
        vec = p.get("embedding_vector")
        if not vec:
            continue
        score = cosine_sim(query_vec, vec)
        scored.append({
            "id": p.get("id"),
            "score": score,
            "embedding_profile_text": p.get("embedding_profile_text", ""),
            "key_values": p.get("key_values", {}),
            "consumer_summary": p.get("consumer_summary", {})
        })
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:max(1, top_k)]


def run_query(product_description):
    client = OpenAI(api_key=OPENAI_API_KEY)
    personas = load_personas(DATABASE_PATH)
    ensure_persona_vectors(personas)
    structured_query = generate_structured_query(client, product_description)
    qvec = embed_query(client, structured_query)
    top = rank_personas(qvec, personas, TOP_K)

    print(f"\nTop {len(top)} matches for: {product_description}\n---")
    for i, r in enumerate(top, start=1):
        preview = (r.get("embedding_profile_text") or "").replace("\n", " ")
        print(f"\n{i}. ID: {r.get('id')}\n   Similarity: {r['score']:.4f}\n   Preview: {preview}")

if __name__ == "__main__":
    product_description = "A high-performance running shoe designed for marathon runners seeking lightweight comfort and superior cushioning."
    run_query(product_description)