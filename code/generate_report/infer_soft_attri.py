#!/usr/bin/env python3
"""
8_infer_soft_attributes.py — Infer coarse, non-sensitive attributes probabilistically.

Inputs:
  - user_personas.csv (needs: user_id, cluster, concat_text)

Outputs:
  - user_soft_attributes.csv
    Columns:
      user_id, cluster,
      p_audience_child, p_audience_teen, p_audience_adult, p_audience_senior, p_audience_unknown,
      p_role_parent, p_role_stylist, p_role_self, p_role_giftgiver, p_role_caregiver, p_role_unknown,
      p_region_us, p_region_uk, p_region_eu, p_region_ca, p_region_other, p_region_unknown,
      pref_size_fit, pref_scent, pref_durability, pref_value_price, pref_comfort, pref_ingredients_allergy,
      pref_shipping_returns, pref_packaging_gift
"""

import os
import re
import argparse
import numpy as np
import pandas as pd

LLM_AVAILABLE = False
try:
    from openai import OpenAI
    LLM_AVAILABLE = True
except Exception:
    pass

def norm_probs(vals):
    s = sum(vals)
    if s <= 0:
        return [0]*len(vals)
    return [v/s for v in vals]

# Simple keyword maps (extend as needed)
KW = {
    "audience_child": r"\b(toddler|baby|infant|kids?|child|children|school)\b",
    "audience_teen": r"\bteen(ager)?s?\b",
    "audience_senior": r"\b(elderly|senior|grand(ma|pa))\b",
    "role_parent": r"\b(my (son|daughter|kid|child)|for my kids|as a parent)\b",
    "role_stylist": r"\b(as a stylist|my clients|salon)\b",
    "role_gift": r"\b(gift(ed)?|present|for (my )?(husband|wife|friend|mom|dad))\b",
    "role_caregiver": r"\b(caregiv(er|ing)|nurse)\b",
    "region_uk": r"\b(colour|favourite|litre|metre|uk|britain|england)\b",
    "region_eu": r"\b(eu|europe|european|euro)\b",
    "region_ca": r"\b(canada|cdn|toronto|vancouver|calgary|ottawa)\b",
    "shipping_returns": r"\b(shipping|arrived|delivery|return(ed)?|refund)\b",
    "size_fit": r"\b(size|sizing|fit|too (small|big)|tight|loose)\b",
    "scent": r"\b(scent|smell|fragrance|odor|perfume)\b",
    "durability": r"\b(broke|last(ed)?|durable|sturdy|quality)\b",
    "value_price": r"\b(price|expensive|overpriced|value|worth)\b",
    "comfort": r"\b(soft|comfortable|itch(y)?|irritat(e|ion))\b",
    "ingredients_allergy": r"\b(ingredient|allergy|sulfate|paraben|silicone|vegan)\b",
    "packaging_gift": r"\b(packaging|package|gift box|giftable|wrap)\b",
}

def score_regex(text, pattern):
    return 1.0 if re.search(pattern, text, flags=re.IGNORECASE) else 0.0

def infer_soft(text):
    t = text or ""
    # Audience probs
    p_child = score_regex(t, KW["audience_child"])
    p_teen = score_regex(t, KW["audience_teen"])
    p_senior = score_regex(t, KW["audience_senior"])
    # default adult if talking about self and not other buckets
    p_adult = 1.0 if (" i " in f" {t.lower()} ") else 0.0
    p_aud = norm_probs([p_child, p_teen, p_adult, p_senior])
    if sum(p_aud) == 0: p_aud = [0,0,0,0]  # unknown later

    # Role probs
    p_parent = score_regex(t, KW["role_parent"])
    p_stylist = score_regex(t, KW["role_stylist"])
    p_gift = score_regex(t, KW["role_gift"])
    p_caregiver = score_regex(t, KW["role_caregiver"])
    p_self = 1.0 if (" i " in f" {t.lower()} ") else 0.0
    p_role = norm_probs([p_parent, p_stylist, p_self, p_gift, p_caregiver])
    if sum(p_role) == 0: p_role = [0,0,0,0,0]  # unknown later

    # Region probs
    p_uk = score_regex(t, KW["region_uk"])
    p_eu = score_regex(t, KW["region_eu"])
    p_ca = score_regex(t, KW["region_ca"])
    p_us = 1.0 if ("color" in t.lower() or "favorite" in t.lower()) else 0.0  # extremely weak proxy
    p_reg = norm_probs([p_us, p_uk, p_eu, p_ca])
    if sum(p_reg) == 0: p_reg = [0,0,0,0]  # unknown later

    # Preferences (binary-ish scores)
    prefs = {
        "pref_size_fit": score_regex(t, KW["size_fit"]),
        "pref_scent": score_regex(t, KW["scent"]),
        "pref_durability": score_regex(t, KW["durability"]),
        "pref_value_price": score_regex(t, KW["value_price"]),
        "pref_comfort": score_regex(t, KW["comfort"]),
        "pref_ingredients_allergy": score_regex(t, KW["ingredients_allergy"]),
        "pref_shipping_returns": score_regex(t, KW["shipping_returns"]),
        "pref_packaging_gift": score_regex(t, KW["packaging_gift"]),
    }

    return {
        "p_audience_child": p_aud[0],
        "p_audience_teen": p_aud[1],
        "p_audience_adult": p_aud[2],
        "p_audience_senior": p_aud[3],
        "p_audience_unknown": 1.0 if sum(p_aud) == 0 else 0.0,
        "p_role_parent": p_role[0],
        "p_role_stylist": p_role[1],
        "p_role_self": p_role[2],
        "p_role_giftgiver": p_role[3],
        "p_role_caregiver": p_role[4],
        "p_role_unknown": 1.0 if sum(p_role) == 0 else 0.0,
        "p_region_us": p_reg[0],
        "p_region_uk": p_reg[1],
        "p_region_eu": p_reg[2],
        "p_region_ca": p_reg[3],
        "p_region_other": 0.0,  # reserved
        "p_region_unknown": 1.0 if sum(p_reg) == 0 else 0.0,
        **prefs
    }

def main():
    ap = argparse.ArgumentParser(description="Infer soft, probabilistic attributes per user")
    ap.add_argument("--users", default="user_personas.csv")
    ap.add_argument("--out", default="user_soft_attributes.csv")
    args = ap.parse_args()

    df = pd.read_csv(args.users)
    out = []
    for _, r in df.iterrows():
        d = infer_soft(str(r.get("concat_text", "")))
        d.update({"user_id": r["user_id"], "cluster": r["cluster"]})
        out.append(d)

    pd.DataFrame(out).to_csv(args.out, index=False)
    print(f"Saved: {args.out}")

if __name__ == "__main__":
    main()
