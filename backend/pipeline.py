import time
from openai import OpenAI
from config import OPENAI_API_KEY, TOP_K

from persona_search import embed_query, get_persona_index_cached, rank_personas_fast
from persona_cluster import (
    cluster_personas,
    fetch_consumer_summaries,
    extract_demographics,
    calculate_gender_distribution,
    calculate_age_distribution,
)
from persona_tagging import generate_consumer_tags_batched

def query(product_description: str):
    client = OpenAI(api_key=OPENAI_API_KEY)

    M, meta_list = get_persona_index_cached()

    qvec = embed_query(client, product_description)

    top_personas = rank_personas_fast(qvec, M, meta_list, TOP_K)
    print(f"\n✅ Retrieved top {len(top_personas)} personas for '{product_description}'.")

    gender_distribution = calculate_gender_distribution(top_personas)
    age_distribution = calculate_age_distribution(top_personas)

    cluster_pids, cluster_counts = cluster_personas(top_personas, w_text=1.0, w_num=2.0)

    consumer_summaries = fetch_consumer_summaries(top_personas, cluster_pids)
    cluster_demographics = extract_demographics(top_personas, cluster_pids)

    profiles = generate_consumer_tags_batched(client, product_description, consumer_summaries)

    customer_profile = {}
    total_personas = len(top_personas)
    for cluster_id, tags_data in profiles.items():
        count = cluster_counts.get(cluster_id, 0)
        percentage = round((count / total_personas) * 100, 1) if total_personas > 0 else 0
        customer_profile[f"cluster{cluster_id}"] = {
            "tags": tags_data.get("tags", []),
            "demographics": cluster_demographics.get(cluster_id, {}),
            "pid": cluster_pids.get(cluster_id, ""),
            "percentage": percentage
        }

    return {
        "gender_distribution": gender_distribution,
        "age_distribution": age_distribution,
        "customer_profile": customer_profile
    }

if __name__ == "__main__":
    product_description = "Walking cane designed for elderly individuals seeking enhanced stability and comfort during mobility."

    start = time.perf_counter()
    result = query(product_description)
    end = time.perf_counter()

    for key, res in result.items():
        print(f"\n--- {key} ---")
        print(res)

    print(f"\n⏱️ Total process time: {end - start:.2f} seconds")
