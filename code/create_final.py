#!/usr/bin/env python3
"""
10_make_deliverables.py — Join everything and produce final persona reports.

Inputs:
  - user_personas.csv        (from 56.py)
  - cluster_summary.csv      (from 56.py)
  - cluster_names.csv        (from 7_name_personas.py)
  - user_soft_attributes.csv (from 8_infer_soft_attributes.py)

Outputs:
  - user_personas_enriched.csv
  - cluster_report.json
  - cluster_report.md
"""

import argparse
import json
import pandas as pd

def main():
    ap = argparse.ArgumentParser(description="Package final persona deliverables")
    ap.add_argument("--users", default="user_personas.csv")
    ap.add_argument("--clusters", default="cluster_summary.csv")
    ap.add_argument("--names", default="cluster_names.csv")
    ap.add_argument("--soft", default="user_soft_attributes.csv")
    ap.add_argument("--out-users", default="user_personas_enriched.csv")
    ap.add_argument("--out-json", default="cluster_report.json")
    ap.add_argument("--out-md", default="cluster_report.md")
    args = ap.parse_args()

    users = pd.read_csv(args.users)
    clusters = pd.read_csv(args.clusters)
    names = pd.read_csv(args.names) if args.names and len(args.names) > 0 else pd.DataFrame(columns=["cluster","label_final","description","evidence_terms"])
    soft = pd.read_csv(args.soft) if args.soft and len(args.soft) > 0 else pd.DataFrame()

    # Merge names into clusters
    clusters2 = clusters.merge(names, on="cluster", how="left")

    # Enrich users with final persona label
    users2 = users.merge(clusters2[["cluster", "label_final", "description"]], on="cluster", how="left")
    # Merge soft attributes if present
    if not soft.empty:
        users2 = users2.merge(soft, on=["user_id", "cluster"], how="left")

    # Save enriched per-user
    users2.to_csv(args.out-users, index=False)  # noqa: E999 (hyphen in attribute name is not valid)
    # Work around hyphen in var name:
    out_users_path = getattr(args, "out_users", "user_personas_enriched.csv")
    users2.to_csv(out_users_path, index=False)

    # Build cluster JSON report
    clusters2["top_terms_list"] = clusters2["top_terms"].fillna("").apply(lambda s: [t.strip() for t in str(s).split(",") if t.strip()])
    clist = []
    for _, r in clusters2.iterrows():
        cid = int(r["cluster"])
        subset = users2[users2["cluster"] == cid]
        entry = {
            "cluster": cid,
            "label": r.get("label_final") or r.get("persona_label") or f"Cluster {cid}",
            "description": r.get("description", ""),
            "size": int(r["size"]),
            "median_rating": r.get("median_rating"),
            "avg_rating": r.get("avg_rating"),
            "pct_verified": r.get("pct_verified"),
            "avg_helpful_votes": r.get("avg_helpful_votes"),
            "top_terms": r.get("top_terms_list", []),
            "example_user_ids": subset["user_id"].head(10).tolist(),
        }
        # If soft attributes present, aggregate means
        soft_cols = [c for c in subset.columns if c.startswith("p_") or c.startswith("pref_")]
        if soft_cols:
            entry["soft_attribute_means"] = subset[soft_cols].mean(numeric_only=True).to_dict()
        clist.append(entry)

    with open(args.out_json, "w") as f:
        json.dump({"clusters": clist}, f, indent=2)

    # Markdown summary
    lines = ["# Persona Cluster Report\n"]
    for c in clist:
        lines.append(f"## Cluster {c['cluster']}: {c['label']}")
        if c["description"]:
            lines.append(f"*{c['description']}*")
        lines.append(f"- Size: **{c['size']}**")
        lines.append(f"- Median rating: **{c['median_rating']}**, Avg rating: **{c['avg_rating']}**")
        lines.append(f"- % Verified: **{c['pct_verified']:.2f}**; Avg helpful votes: **{c['avg_helpful_votes']:.2f}**")
        if c["top_terms"]:
            lines.append(f"- Top terms: `{', '.join(c['top_terms'])}`")
        if "soft_attribute_means" in c:
            lines.append(f"- Soft attributes (means):")
            for k, v in c["soft_attribute_means"].items():
                lines.append(f"  - {k}: {v:.3f}")
        lines.append("")
    with open(args.out_md, "w") as f:
        f.write("\n".join(lines))

    print(f"Saved enriched users: {out_users_path}")
    print(f"Saved JSON report:   {args.out_json}")
    print(f"Saved Markdown:      {args.out_md}")

if __name__ == "__main__":
    main()
