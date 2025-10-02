#!/usr/bin/env python3
"""
7_name_personas.py — Improve cluster names and add short descriptions.

Inputs (from 56.py):
  - user_personas.csv
      columns used: user_id, cluster, persona_label, concat_text,
                    avg_rating, pct_verified_purchase, avg_helpful_votes
  - cluster_summary.csv
      columns used: cluster, size, median_rating, avg_rating,
                    pct_verified, avg_helpful_votes, top_terms

Outputs:
  - cluster_names.csv    (cluster, label_final, description, evidence_terms)
"""

import os
import argparse
import pandas as pd
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv
import colorful as cf
from tqdm import tqdm
load_dotenv()

PROMPT = """You are naming user persona clusters derived from product reviews.
Given:
- Top keywords: {terms}
- Cluster stats: size={size}, median_rating={median_rating:.2f}, avg_rating={avg_rating:.2f}, pct_verified={pct_verified:.2f}, avg_helpful_votes={avg_helpful_votes:.2f}
- Representative snippets:
{snips}

Return:
1) A concise persona NAME (3–6 words, no emojis).
2) A one-sentence DESCRIPTION of the persona; avoid demographics unless explicitly indicated by text (e.g., 'parents', 'stylists'), and never guess age or sensitive info.

Format exactly as:
NAME: <short name>
DESCRIPTION: <one sentence>
"""

def llm_refine(terms, stats, snippets, model="gpt-4o-mini"):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    snip_text = "\n".join(f"- {s}" for s in snippets if s)
    msg = PROMPT.format(
        terms=", ".join(terms) if terms else "N/A",
        size=stats.get("size", 0),
        median_rating=float(stats.get("median_rating", 0) or 0),
        avg_rating=float(stats.get("avg_rating", 0) or 0),
        pct_verified=float(stats.get("pct_verified", 0) or 0),
        avg_helpful_votes=float(stats.get("avg_helpful_votes", 0) or 0),
        snips=snip_text or "- (no short snippets available)"
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": msg}],
    )
    return resp.choices[0].message.content.strip()

def heuristic_label(terms, stats):
    rating = stats.get("median_rating", None)
    if rating is None or pd.isna(rating):
        tone = "Mixed-rating"
    elif rating <= 2.5:
        tone = "Critical"
    elif rating >= 4.0:
        tone = "Enthusiastic"
    else:
        tone = "Mixed-rating"
    head = " / ".join(terms[:2]) if terms else "General"
    name = f"{tone} • {head}".strip(" •")
    desc = "Users with similar themes reflected in top terms and review statistics."
    return name, desc

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Refine persona labels and add descriptions")
    ap.add_argument("--users", default="./data/user_personas.csv", help="Per-user assignments from 56.py")
    ap.add_argument("--clusters", default="./data/cluster_summary.csv", help="Per-cluster summary from 56.py")
    ap.add_argument("--out", default="./data/cluster_names.csv", help="Output CSV with final labels/descriptions")
    ap.add_argument("--snippets-per-cluster", type=int, default=5, help="How many short snippets to pass to the LLM/heuristic")
    ap.add_argument("--llm-model", default="gpt-5-mini")
    args = ap.parse_args()
    print(cf.bold(cf.green("Begin persona generation...")))

    # Load inputs (from 56.py)
    users = pd.read_csv(args.users)
    clusters = pd.read_csv(args.clusters)

    # Basic schema checks (tolerant but informative)
    for col in ["cluster", "size", "median_rating", "avg_rating", "pct_verified", "avg_helpful_votes", "top_terms"]:
        if col not in clusters.columns:
            raise ValueError(f"cluster_summary.csv is missing required column: {col}")
    for col in ["user_id", "cluster", "concat_text", "avg_rating", "pct_verified_purchase", "avg_helpful_votes"]:
        if col not in users.columns:
            raise ValueError(f"user_personas.csv is missing required column: {col}")

    # Representative snippets per cluster: choose shortest texts for readability
    reps = (
        users.assign(_len=users["concat_text"].fillna("").str.len())
             .sort_values(["cluster", "_len"])
             .groupby("cluster", as_index=False)
             .head(args.snippets_per_cluster)
    )

    out_rows = []
    print(cf.bold(cf.green("Using LLM to create persona")))
    for _, row in tqdm(clusters.iterrows()):
        cid = int(row["cluster"])

        # Parse top_terms from 56.py (comma-separated string)
        raw_terms = str(row.get("top_terms", "") or "")
        terms = [t.strip() for t in raw_terms.split(",") if t.strip()]

        stats = {
            "size": int(row.get("size", 0)),
            "median_rating": float(row.get("median_rating", 0) or 0),
            "avg_rating": float(row.get("avg_rating", 0) or 0),
            "pct_verified": float(row.get("pct_verified", 0) or 0),
            "avg_helpful_votes": float(row.get("avg_helpful_votes", 0) or 0),
        }

        snips = reps.loc[reps["cluster"] == cid, "concat_text"].fillna("").tolist()

        
        llm_out = llm_refine(terms, stats, snips, model=args.llm_model)
        # Parse the strict two-line format
        name, desc = None, None
        for line in llm_out.splitlines():
            u = line.strip()
            if u.upper().startswith("NAME:"):
                name = u.split(":", 1)[1].strip()
            elif u.upper().startswith("DESCRIPTION:"):
                desc = u.split(":", 1)[1].strip()
        if not name or not desc:
            name, desc = heuristic_label(terms, stats)

        out_rows.append({
            "cluster": cid,
            "label_final": name,
            "description": desc,
            "evidence_terms": ", ".join(terms)
        })

    pd.DataFrame(out_rows).to_csv(args.out, index=False)
    print(cf.bold(cf.green("Completed process")))
