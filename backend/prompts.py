import json
from typing import Dict, Optional, List, Any

# ============================================================================
# SYSTEM PROMPTS
# ============================================================================

DETAILED_ANALYSIS_SYSTEM_PROMPT = (
    "You simulate a real consumer and must output strictly valid JSON that matches the schema. "
    "Do not invent brands, prices, or statistics unless they appear in <FACTS>. "
    "Keep the writing concrete, first person, and 2-3 sentences."
)

PURCHASE_DECISION_SYSTEM_PROMPT = (
    "You simulate a consumer deciding whether to buy a product. "
    "Respond ONLY with 'yes' or 'no' — nothing else. "
    "Answer as quickly as possible. No punctuation, no explanation."
)

PERSONA_GENERATION_SYSTEM_PROMPT = "You are a branding and consumer-insight strategist."

PERSONA_CLASSIFICATION_SYSTEM_PROMPT = (
    "You are a professional consumer researcher and behavioral analyst. "
    "Your job is to categorize real personas into predefined consumer archetypes based on "
    "their tone, values, motivations, lifestyle, and behavioral patterns. "
    "Each target persona archetype represents a distinct kind of consumer (for example, "
    "someone might be achievement-oriented, thrill-seeking, pragmatic, health-focused, or tech-obsessed). "
    "\n\n"
    "Follow these rules strictly:\n"
    "1. Read the persona summary carefully and infer what kind of person they are — their habits, values, goals, and emotional tone.\n"
    "2. Compare these traits to the target archetypes listed.\n"
    "3. Choose the one archetype that BEST fits this person, even if the match is not perfect.\n"
    "4. Aim for a reasonably balanced distribution of archetypes overall — avoid assigning too many personas to the same archetype unless clearly justified.\n"
    "5. If multiple archetypes could apply, prefer one that seems underrepresented or distinct from the majority.\n"
    "6. If none clearly fits, respond with 'Other'.\n"
    "7. Return ONLY the archetype title exactly as written in the provided list, or 'Other'.\n"
)

RELEVANT_PERSONA_SELECTION_SYSTEM_PROMPT = (
    "You are a consumer psychology assistant. "
    "Given a product description and a fixed list of allowed personality attributes, "
    "choose ONLY from the allowed attributes. Be precise and conservative."
)

# ============================================================================
# USER PROMPT TEMPLATES
# ============================================================================

def get_relevant_personality_prompt(product_description, attributes) -> str:
    allowed_block = "\n".join(f"- {a}" for a in attributes)
    return (
        f"Product Description:\n"
        f"\"\"\"\n{product_description}\n\"\"\"\n\n"
        f"Allowed Personality Attributes (use EXACT spelling; case-sensitive):\n"
        f"{allowed_block}\n\n"
        f"Task: Choose EXACTLY 5 MOST RELEVANT attributes that best characterize "
        f"the typical customer attracted to this product. Use ONLY the allowed attributes. "
        f"Order them by relevance (most relevant first).\n\n"
        f"Output format (STRICT): a JSON array of strings of length 5.\n"
        f"Example:\n"
        f'["Frugal","Tech Savvy","Eco Minded","Practical","Curious","Organized"]\n\n'
        f"Do NOT include explanations, keys, markdown, or extra text."
    )


def get_detailed_analysis_prompt(
    persona_summary: str,
    question: str,
    jitter: int,
    facts: Optional[Dict] = None
) -> str:
    facts_json = json.dumps(facts or {}, ensure_ascii=False)

    return f"""
<PROFILE>
{persona_summary}
</PROFILE>

<QUESTION>
{question}
</QUESTION>

<FACTS>
{facts_json}
</FACTS>

Decision steps (follow exactly):

1) Likelihood → score:
   - Interpret S as how strongly this persona would agree or act on the question (1–10 scale).
   - 1 = very unlikely, 10 = very likely.
   - Base S on the persona's tone and intent: if they express clear willingness, high interest, or frequent similar behavior, set S = 8–10.
   - If they sound hesitant, conditional, or selective, set S = 4–7.
   - If they reject the idea or rarely do this behavior, set S = 1–3.

2) Feature adjustments (apply all that fit the profile):
   +2 if the sender is a favorite category/brand **explicitly** in <FACTS>.
   +2 if "deal_threshold_pct" in <FACTS> is met by the offer in the question.
   +1 if budget is tight but the persona actively hunts promos.
   -2 if inbox volume ≥ 100/day, 'unsubscribe spree', or privacy-paranoid.
   -1 if time pressure is high or promo fatigue is high.

3) Add deterministic jitter J = {jitter} (do not mention J). New S = S + J.

4) Clamp S to 1..10.

5) Text: Write 2-3 sentences in first person that reflect the decision and mention exactly one everyday constraint that fits the profile (money, time, space, location, family). No brand/statistic unless in <FACTS>. Be specific; avoid hedging.

Choose one "micro-scenario" that matches the profile and reflect it in wording (do not name the scenario):
[Inbox-zero purge] [Deal-hunter watching % threshold] [Brand loyalist] [Privacy-first] [Time-crunched skimmer].

Output ONLY the following JSON (strict format):
{{
  "text": "…1–2 sentences, first person…",
  "score": S (integer 1..10),
  "assumption": "…only if you made one, else empty string…"
}}
"""


def get_purchase_decision_prompt(persona_summary: str, product_description: str) -> str:
    """
    Generate the purchase decision user prompt.

    Args:
        persona_summary: The persona's summary text
        product_description: Product description to evaluate

    Returns:
        Formatted user prompt string
    """
    return f"""
<PROFILE>
{persona_summary}
</PROFILE>

<PRODUCT>
{product_description}
</PRODUCT>

Would this persona likely purchase the product? Reply only 'yes' or 'no'.
"""

def get_persona_generation_prompt(product_description: str, num_personas: int = 5) -> str:
    return f"""Based on the product description below, generate {num_personas}–{num_personas + 1} concise marketing personas that reflect the main consumer types most likely to buy or identify with this product.

Each persona title should be:
- 1-2 words long
- Distinct in mindset, lifestyle, or motivation
- Broad enough for marketing segmentation (not overly specific)
- Evocative and human (sounds like a type of buyer)
- Nothing overly cute or creative. They have to be clear and professional. 
- Title-case formatted, like:
  * "Athlete"
  * "Gamer"
  * "Health Conscious"
  * "Budget Conscious"
  * "Tech Enthusiast"

Additionally, identify the demographic profile of potential customers:
- Select one or more age ranges that are most likely to purchase this product from: "18-29", "30-49", "50-64", "65+"
- Select the gender(s) most likely to purchase: "Male", "Female", or "Both"

Return your response as a JSON object with the following format:
{{
  "personas": ["Active Achiever", "Status Seeker", "Health Pursuer", "Value Maximizer", "Trend Follower"],
  "age_ranges": ["30-49", "50-64"],
  "gender": "Both"
}}

<PRODUCT>
{product_description}
</PRODUCT>"""


def get_persona_classification_prompt(
    generated_titles: List[str],
    persona_summary: str,
    persona_attributes: Dict[str, Any],
) -> str:
    """
    Build a prompt that uses both the narrative summary and the structured attributes
    to classify into one of the provided archetype titles.
    """
    titles_str = "\n".join(f"- {t}" for t in generated_titles)
    attrs_str = json.dumps(persona_attributes, ensure_ascii=False, indent=2)

    user_prompt = f"""You will receive a consumer persona summary, structured persona attributes, and
a set of possible archetype titles. Your task is to pick the single best-fitting archetype.

<PERSONA_SUMMARY>
{persona_summary}
</PERSONA_SUMMARY>

<PERSONA_ATTRIBUTES_JSON>
{attrs_str}
</PERSONA_ATTRIBUTES_JSON>

<TARGET_ARCHETYPES>
{titles_str}
</TARGET_ARCHETYPES>

Instructions:
1) Read BOTH the summary and attributes. Weigh explicit attributes (e.g., Big-5, values, goals, constraints) heavily.
2) Match traits, motivations, behaviors, and constraints to the closest archetype title.
3) If multiple titles seem close, break ties by:
   a) Value alignment > Behavioral patterns > Demographic fit > Tone/style.
4) Output ONLY the best-fitting archetype title EXACTLY as written from the list above.

Think step by step:
- Briefly align key attributes (values, behaviors, constraints) to 1–3 candidate titles.
- Choose the best title and output ONLY that title (no punctuation, no explanation).
"""
    return user_prompt