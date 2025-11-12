import os
import json
import sys
from typing import List, Dict, Any
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.decomposition import TruncatedSVD
import matplotlib.pyplot as plt
import re
from openai import OpenAI
import numpy as np
from utils import (
    load_personas,
    l2_normalize,
    cosine_sim,
    ensure_persona_vectors,
    stabilize_embeddings,
)

# --------------------------------------------------
# Import configuration from parent directory
# --------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import EMBEDDING_MODEL, OPENAI_API_KEY, TOP_K, DATABASE_PATH, CHAT_MODEL


# --------------------------------------------------
# Embedding and query helpers
# --------------------------------------------------
def generate_structured_query(client: OpenAI, product_description: str) -> str:
    system_prompt = (
        "You are a market psychologist. Rewrite the given product description "
        "into a structured, persona-compatible summary emphasizing how the "
        "product aligns with consumer values, motivations, risk attitudes, "
        "emotional appeal, and lifestyle context. Keep it short (≈5–7 sentences)."
    )
    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": product_description},
        ],
    )
    return resp.choices[0].message.content.strip()


def embed_query(client: OpenAI, text: str) -> List[float]:
    resp = client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return l2_normalize(resp.data[0].embedding)


# --------------------------------------------------
# Persona ranking (by embedding_profile_text)
# --------------------------------------------------
def rank_personas(query_vec: List[float], personas: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
    scored = []
    for p in personas:
        text_vec = p.get("embedding_vector")
        if not text_vec:
            continue
        score = cosine_sim(query_vec, text_vec)
        scored.append({
            "id": p.get("id"),
            "score": score,
            "embedding_profile_text": p.get("embedding_profile_text", ""),
            "key_values": p.get("key_values", {}),
            "consumer_summary": p.get("consumer_summary", {}),
            "cluster_embedding_vector": p.get("cluster_embedding_vector", []),
        })
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:max(1, top_k)]


# --------------------------------------------------
# K-Means clustering (on cluster_embedding_vector)
# --------------------------------------------------
def cluster_personas(personas: List[Dict[str, Any]], k: int = None, visualize: bool = True) -> Dict[int, str]:
    X = np.array([p["cluster_embedding_vector"] for p in personas], dtype=np.float32)
    X = stabilize_embeddings(X)

    # Auto-select k if not provided
    if k is None:
        scores = []
        for n in range(3, min(10, len(personas))):
            km = KMeans(n_clusters=n, n_init=10, random_state=42).fit(X)
            scores.append((n, silhouette_score(X, km.labels_)))
        k = max(scores, key=lambda x: x[1])[0]
        print(f"🧠 Auto-selected k={k} based on silhouette score")

    km = KMeans(n_clusters=k, n_init=20, random_state=42)
    labels = km.fit_predict(X)
    centroids = km.cluster_centers_

    if visualize:
        svd = TruncatedSVD(n_components=2, random_state=42)
        coords = svd.fit_transform(X)
        plt.figure(figsize=(6, 5))
        plt.scatter(coords[:, 0], coords[:, 1], c=labels, cmap="tab10", s=40, alpha=0.7)
        plt.scatter(
            svd.transform(km.cluster_centers_)[:, 0],
            svd.transform(km.cluster_centers_)[:, 1],
            c="black", marker="x", s=100, label="Centroids"
        )
        plt.legend()
        plt.title(f"K-Means Clustering of {len(personas)} Personas (k={k})")
        plt.xlabel("SVD-1")
        plt.ylabel("SVD-2")
        #plt.show()

    cluster_centroid_pids = {}
    for cluster_id in range(k):
        centroid = centroids[cluster_id]
        # Find the single persona closest to this centroid
        closest_persona = min(
            personas,
            key=lambda p: np.linalg.norm(np.array(p["cluster_embedding_vector"]) - centroid)
        )
        cluster_centroid_pids[cluster_id] = closest_persona["id"]

    print("\n✅ Cluster centroid PIDs computed (1 per cluster).")
    return cluster_centroid_pids


# --------------------------------------------------
# Fetch consumer summaries for centroid PIDs
# --------------------------------------------------
def fetch_consumer_summaries(personas: List[Dict[str, Any]], centroid_pids: Dict[int, str]) -> Dict[int, Dict[str, str]]:
    pid_to_persona = {p["id"]: p for p in personas}
    consumer_summaries = {}

    for cluster_id, pid in centroid_pids.items():
        if pid in pid_to_persona:
            consumer_summaries[cluster_id] = pid_to_persona[pid].get("consumer_summary", {})

    return consumer_summaries


# --------------------------------------------------
# Extract demographic information for centroid PIDs
# --------------------------------------------------
def extract_demographics(personas: List[Dict[str, Any]], centroid_pids: Dict[int, str]) -> Dict[int, Dict[str, str]]:
    pid_to_persona = {p["id"]: p for p in personas}
    demographics_info = {}

    for cluster_id, pid in centroid_pids.items():
        if pid in pid_to_persona:
            demographics_str = pid_to_persona[pid].get("key_values", {}).get("demographics", "")

            # Extract specific demographic fields
            demo_dict = {}

            # Extract Gender
            gender_match = re.search(r"Gender:\s*(\w+)", demographics_str)
            if gender_match:
                demo_dict["gender"] = gender_match.group(1)

            # Extract Age
            age_match = re.search(r"Age:\s*([\d\-\+]+)", demographics_str)
            if age_match:
                demo_dict["age"] = age_match.group(1)

            # Extract Marital status
            marital_match = re.search(r"Marital status:\s*([^\n]+)", demographics_str)
            if marital_match:
                demo_dict["marital_status"] = marital_match.group(1).strip()

            # Extract Income
            income_match = re.search(r"Income:\s*([^\n]+)", demographics_str)
            if income_match:
                demo_dict["income"] = income_match.group(1).strip()

            # Extract Employment status
            employment_match = re.search(r"Employment status:\s*([^\n]+)", demographics_str)
            if employment_match:
                demo_dict["employment_status"] = employment_match.group(1).strip()

            demographics_info[cluster_id] = demo_dict

    return demographics_info


# --------------------------------------------------
# Calculate gender distribution from personas
# --------------------------------------------------
def calculate_gender_distribution(personas: List[Dict[str, Any]]) -> Dict[str, int]:
    gender_counts = {"Male": 0, "Female": 0}

    for persona in personas:
        demographics = persona.get("key_values", {}).get("demographics", "")
        if "Gender: Male" in demographics:
            gender_counts["Male"] += 1
        elif "Gender: Female" in demographics:
            gender_counts["Female"] += 1

    return gender_counts


# --------------------------------------------------
# Calculate age distribution from personas
# --------------------------------------------------
def calculate_age_distribution(personas: List[Dict[str, Any]]) -> Dict[str, int]:
    age_counts = {"18-29": 0, "30-49": 0, "50-64": 0, "65+": 0}

    for persona in personas:
        demographics = persona.get("key_values", {}).get("demographics", "")
        if "Age: 18-29" in demographics:
            age_counts["18-29"] += 1
        elif "Age: 30-49" in demographics:
            age_counts["30-49"] += 1
        elif "Age: 50-64" in demographics:
            age_counts["50-64"] += 1
        elif "Age: 65+" in demographics:
            age_counts["65+"] += 1

    return age_counts


# --------------------------------------------------
# Generate consumer profile descriptions using GPT
# --------------------------------------------------

def generate_consumer_tags(client: OpenAI, product_description: str, consumer_summaries: Dict[int, Dict[str, str]]) -> Dict[int, Dict[str, Any]]:
    system_prompt = (
        "You are a consumer behavior analyst. Given a product description and a consumer summary, "
        "generate 6–10 concise TAGS that describe this consumer group's purchasing personality and decision-making traits "
        "as they relate to buying the given product.\n\n"
        "These tags should reflect descriptors such as attitudes toward price (e.g., 'price-sensitive', 'not price-conscious'), "
        "quality (e.g., 'quality-driven', 'value-seeking'), lifestyle (e.g., 'active lifestyle', 'comfort-oriented'), "
        "motivations (e.g., 'safety-focused', 'self-reliance-oriented'), and emotional drivers (e.g., 'confidence-seeking', 'brand-trusting').\n\n"
        "Focus on *how they make purchase decisions*, not demographic traits or product features.\n\n"
        "Do NOT generate a title or summary sentence — only return the descriptive tags.\n\n"
        "Return the output in pure JSON format with one field: 'tags'. No explanations, no markdown, and no code blocks."
    )

    results = {}

    for cluster_id, summary in consumer_summaries.items():
        summary_text = "\n".join([
            f"{key}: {value}"
            for key, value in summary.items()
            if isinstance(value, str)
        ])

        user_prompt = (
            f"Product: {product_description}\n\n"
            f"Consumer Summary:\n{summary_text}\n\n"
            "Generate a JSON object with one field: 'tags'."
        )

        resp = client.chat.completions.create(
            model="gpt-5-nano-2025-08-07",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        content = resp.choices[0].message.content.strip()
        cleaned = re.sub(r"^```(?:json)?|```$", "", content.strip(), flags=re.MULTILINE).strip()

        try:
            parsed = json.loads(cleaned)
            results[cluster_id] = parsed
        except json.JSONDecodeError:
            print(f"⚠️ Warning: Could not parse JSON for Cluster {cluster_id}. Returning raw text.")
            results[cluster_id] = {"tags": [cleaned]}

        print(f"✅ Generated purchase-impact tags for Cluster {cluster_id}")

    return results


# --------------------------------------------------
# Combined runner
# --------------------------------------------------
def query(product_description):
    client = OpenAI(api_key=OPENAI_API_KEY)
    personas = load_personas(DATABASE_PATH)
    ensure_persona_vectors(personas)

    structured_query = generate_structured_query(client, product_description)
    qvec = embed_query(client, structured_query)

    # Step 1: Rank using embedding_profile_text embeddings
    top_personas = rank_personas(qvec, personas, TOP_K)
    print(f"\n✅ Retrieved top {len(top_personas)} personas for '{product_description}'.")

    # Step 2: Calculate gender distribution
    gender_distribution = calculate_gender_distribution(top_personas)
    print(f"\n✅ Gender distribution: {gender_distribution}")

    # Step 3: Calculate age distribution
    age_distribution = calculate_age_distribution(top_personas)
    print(f"\n✅ Age distribution: {age_distribution}")

    # Step 4: Cluster using cluster_embedding_vector
    cluster_pids = cluster_personas(top_personas, 3, visualize=True)

    # Step 5: Fetch consumer summaries for centroid PIDs
    consumer_summaries = fetch_consumer_summaries(top_personas, cluster_pids)
    print(f"\n✅ Fetched consumer summaries for {len(consumer_summaries)} clusters.")

    # Step 6: Extract demographics for centroid PIDs
    cluster_demographics = extract_demographics(top_personas, cluster_pids)
    print(f"\n✅ Extracted demographics for {len(cluster_demographics)} clusters.")

    # Step 7: Generate consumer profile descriptions
    print("\n🧠 Generating consumer profile descriptions...")
    profiles = generate_consumer_tags(client, product_description, consumer_summaries)

    # Step 8: Format customer profile with cluster tags and demographics
    customer_profile = {}
    for cluster_id, tags_data in profiles.items():
        customer_profile[f"cluster{cluster_id}"] = {
            "tags": tags_data.get("tags", []),
            "demographics": cluster_demographics.get(cluster_id, {}),
            "pid": cluster_pids.get(cluster_id, "")
        }

    print("\n✅ Clustering complete. Returning gender distribution, age distribution, and customer profile.")
    return {
        "gender_distribution": gender_distribution,
        "age_distribution": age_distribution,
        "customer_profile": customer_profile
    }


# --------------------------------------------------
# LOCAL TEST
# --------------------------------------------------
if __name__ == "__main__":
    product_description = "Walking cane for elderly users focused on stability and comfort."
    result = query(product_description)
    print(result)
