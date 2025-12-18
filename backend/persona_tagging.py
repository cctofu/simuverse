# persona_tagging.py
from typing import Dict, Any
import json
from openai import OpenAI

def generate_consumer_tags_batched(client: OpenAI, product_description: str, consumer_summaries: Dict[int, Dict[str, str]]):
    cluster_blocks = []
    for cid, summary in consumer_summaries.items():
        summary_text = "\n".join(
            f"{k}: {v}" for k, v in summary.items() if isinstance(v, str)
        )
        cluster_blocks.append(f"Cluster {cid}:\n{summary_text}")
    clusters_str = "\n\n".join(cluster_blocks)

    system_prompt = (
        "You are a senior consumer segmentation strategist.\n"
        "Label each cluster with short TAGS that differentiate it from other clusters.\n\n"
        "Rules:\n"
        "1) Return EXACTLY 4 tags per cluster.\n"
        "2) Each tag MUST be exactly 4–5 words.\n"
        "3) Tags must be derived from the consumer summary (values, cognition, risk, emotions, spending, sustainability), "
        "not product features.\n"
        "4) Avoid filler: focused, oriented, values, traditional, lifestyle, brand, quality, comfort, stability.\n"
        "5) Do NOT include age or gender unless truly distinguishing.\n"
        "6) Return ONLY valid JSON.\n"
    )

    user_prompt = (
        f"Product description (context only; do NOT copy product words into tags):\n"
        f"{product_description}\n\n"
        "Cluster consumer summaries:\n"
        f"{clusters_str}\n\n"
        "For each cluster, output EXACTLY 4 tags. Each tag must be EXACTLY 4–5 words.\n"
        "Do not mention the product, 'walking cane', 'stability', 'comfort', 'elderly'.\n"
        "Return JSON only."
    )

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
    )

    data = json.loads(resp.choices[0].message.content)
    results: Dict[int, Dict[str, Any]] = {}
    for cid_str, cluster_obj in data.get("clusters", {}).items():
        cid = int(cid_str)
        tags = cluster_obj.get("tags", [])
        results[cid] = {"tags": tags[:4]}
    return results
