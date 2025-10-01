#!/usr/bin/env python3
"""
7_name_personas.py — Improve cluster names and add short descriptions.

Inputs:
  - user_personas.csv    (user_id, cluster, persona_label, concat_text, stats)
  - cluster_summary.csv  (cluster, size, median_rating, avg_rating, pct_verified, avg_helpful_votes, top_terms)

Outputs:
  - cluster_names.csv    (cluster, label_final, description, evidence_terms)
"""

import os
import argparse
import pandas as pd
import numpy as np

LLM_AVAILABLE = False
try:
    from openai import OpenAI
    LLM_AVAILABLE = True
except Exception:
    pass

PROMPT = """You are naming user persona clusters derived from product reviews.
Given:
- Top keywords: {terms}
- Cluster stats: size={size}, median_rating={median_rating:.2f}, avg_rating={avg_rating:.2f}, pct_verified={pct_verified:.2f}, avg_helpful_votes={avg_helpful_votes:.2f}
- Representative snippets:
{snips}

Return:
1) A concise persona NAME (3–6 words, no emojis).
2) A one-sentence DESCRIPTION of the persona; avoid demographics unless explicitly indicated by text (e.g., 'parents', 'stylists'), and never guess age or sensitive info.

Format:
NAME: <short name>
DESCRIPTION: <one sentence>
"""

def llm_refine(terms, stats, snippets, model="gpt-4o-mini"):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    snip_text = "\n".join([f"- {s}" for s in snippets])
    msg = PROMPT.format(
        terms=", ".join(terms),
        size=stats["size"],
        median_rating=stats.get("median_rating", np.nan) or 0.0,
        avg_rating=stats.get("avg_rating", np.nan) or 0.0,
        pct_verified=stats.get("pct_verified", np.nan) or 0.0,
        avg_helpful_votes=stats.get("avg_helpful_votes", np.nan) or 0.0,
        snips=snip_text
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": msg}],
        temperature=0.3,
    )
    return resp.choices[0].message.content.strip()

def heuristic_label(terms, stats):
    rating = stats.get("median_rating", None)
    if rating is None:
        tone = "Mixed-rating"
    elif rating <= 2.5:
        tone = "Critical"
    elif rating >= 4.0:
        tone = "Enthusiastic"
    else:
        tone = "Mixed-rating"
    head = " / ".join(terms[:2]) if terms else "General"
    return f"{tone} • {head}", "Users sharing similar concerns/interests reflected in the top terms and review statistics."

def main():
    ap = argparse.ArgumentParser(description="Refine persona labels and add descriptions")
    ap.add_argument("--users", default="user_personas.csv")
    ap.add_argument("--clusters", default="cluster_summary.csv")
    ap.add_argument("--out", default="cluster_names.csv")
    ap.add_argument("--snippets-per-cluster", type=int, default=5)
    ap.add_argument("--llm", action="store_true", help="Use OpenAI to refine labels (requires OPENAI_API_KEY)")
    ap.add_argument("--llm-model", default="gpt-4o-mini")
    args = ap.parse_args()

    users = pd.read_csv(args.users)
    clusters = pd.read_csv(args.clusters)

    # Collect representative snippets per cluster (closest we have: shortest texts to keep readable)
    reps = (users.assign(text_len=users["concat_text"].fillna("").str.len())
                 .sort_values(["cluster", "text_len"])
                 .groupby("cluster")
                 .head(args.snippets_per_cluster))

    out_rows = []
    for _, row in clusters.iterrows():
        cid = int(row["cluster"])
        terms = [t.strip() for t in str(row.get("top_terms", "")).split(",") if t.strip()]
        stats = {
            "size": int(row.get("size", 0)),
            "median_rating": float(row.get("median_rating", 0) or 0),
            "avg_rating": float(row.get("avg_rating", 0) or 0),
            "pct_verified": float(row.get("pct_verified", 0) or 0),
            "avg_helpful_votes": float(row.get("avg_helpful_votes", 0) or 0),
        }
        snips = reps.loc[reps["cluster"] == cid, "concat_text"].fillna("").tolist()

        if args.llm and LLM_AVAILABLE and os.getenv("OPENAI_API_KEY"):
            try:
                llm_out = llm_refine(terms, stats, snips, model=args.llm_model)
                # Parse simple two-line format
                name, desc = None, None
                for line in llm_out.splitlines():
                    if line.upper().startswith("NAME:"):
                        name = line.split(":", 1)[1].strip()
                    if line.upper().startswith("DESCRIPTION:"):
                        desc = line.split(":", 1)[1].strip()
                if not name or not desc:
                    name, desc = heuristic_label(terms, stats)
            except Exception:
                name, desc = heuristic_label(terms, stats)
        else:
            name, desc = heuristic_label(terms, stats)

        out_rows.append({
            "cluster": cid,
            "label_final": name,
            "description": desc,
            "evidence_terms": ", ".join(terms)
        })

    pd.DataFrame(out_rows).to_csv(args.out, index=False)
    print(f"Saved: {args.out}")

if __name__ == "__main__":
    main()
