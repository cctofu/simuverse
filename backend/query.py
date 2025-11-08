import random
from typing import Dict, Any
from utils import (
    generate_relevant_personas,
    find_top_personas,
    analyze_purchase_decisions,
    classify_yes_personas,
    generate_product_personas,
    generate_persona_insights
)

def run_query(product_description: str) -> Dict[str, Any]:
    print(f"🚀 Running persona flow for: {product_description}")

    # Step 1: Generate 5 relevant personas
    personas = generate_relevant_personas(product_description)
    print(f"✅ Generated {len(personas)} personas")

    # Step 2: Generate product personas with demographics
    product_persona_data = generate_product_personas(product_description)
    product_persona = product_persona_data.get("personas", [])
    age_ranges = product_persona_data.get("age_ranges", [])
    gender = product_persona_data.get("gender", "Both")
    print(f"✅ Generated {len(product_persona)} product personas")
    print(f"📊 Demographics - Age ranges: {age_ranges}, Gender: {gender}")

    # Step 3: Find top 10 similar personas from database
    topk = find_top_personas(personas, top_k=10)
    print(f"✅ Found {len(topk)} top personas (most similar profiles)")

    # Step 4: Analyze purchase decisions with demographic filtering
    analysis_results = analyze_purchase_decisions(
        product_description=product_description,
        age_ranges=age_ranges,
        gender=gender
    )
    print(f"✅ Purchase analysis completed")

    # Step 5: Classify 'yes' personas
    yes_personas = [p for p in analysis_results["details"] if p["decision"] == "yes"]
    classified_yes = classify_yes_personas(yes_personas, product_persona)
    print(f"✅ Classified {len(classified_yes)} 'yes' personas")

    # Count would_buy_pie responses
    would_buy_pie_counts = {"yes": 0, "no": 0}
    if analysis_results and "details" in analysis_results:
        for detail in analysis_results["details"]:
            decision = detail.get("decision", "").lower()
            if decision == "yes":
                would_buy_pie_counts["yes"] += 1
            elif decision == "no":
                would_buy_pie_counts["no"] += 1

    # Count yes_pie - distribution of yes personas across product personas
    yes_pie_counts = {}
    if product_persona:
        # Initialize all product personas with 0 count
        for persona in product_persona:
            yes_pie_counts[persona] = 0

    if classified_yes:
        # Count how many yes personas are classified into each product persona
        for classification in classified_yes:
            persona_type = classification.get("assigned_archetype", "")
            if persona_type in yes_pie_counts:
                yes_pie_counts[persona_type] += 1

    # Count age_distribution - distribution of all personas across age ranges
    age_distribution = {
        "18-29": 0,
        "30-49": 0,
        "50-64": 0,
        "65+": 0
    }

    if analysis_results and "details" in analysis_results:
        for detail in analysis_results["details"]:
            age = detail.get("age")
            if age is not None:
                age_str = str(age).strip()
                # Handle both string ranges and numeric values
                if age_str in ["18-29", "30-49", "50-64"]:
                    age_distribution[age_str] += 1
                elif age_str == "65" or age_str.startswith("65"):
                    age_distribution["65+"] += 1
                else:
                    # Try to parse as numeric if it's not a range string
                    try:
                        age_val = int(age_str)
                        if 18 <= age_val <= 29:
                            age_distribution["18-29"] += 1
                        elif 30 <= age_val <= 49:
                            age_distribution["30-49"] += 1
                        elif 50 <= age_val <= 64:
                            age_distribution["50-64"] += 1
                        elif age_val >= 65:
                            age_distribution["65+"] += 1
                    except (ValueError, TypeError):
                        pass  # Skip invalid age values

    # Select one random persona from each product_persona category (if count >= 1)
    selected_consumer = {}

    if classified_yes and analysis_results and "details" in analysis_results:
        # Group classified yes personas by product persona type
        personas_by_type = {}
        for classification in classified_yes:
            persona_type = classification.get("assigned_archetype", "")
            persona_id = classification.get("persona_id", "")

            if persona_type not in personas_by_type:
                personas_by_type[persona_type] = []
            personas_by_type[persona_type].append(persona_id)

        # For each product persona type with at least 1 persona, randomly select one
        for persona_type, persona_ids in personas_by_type.items():
            if len(persona_ids) >= 1:
                # Randomly select one persona_id from this type
                selected_id = random.choice(persona_ids)

                # Find the persona_summary for this selected persona
                for detail in analysis_results["details"]:
                    if detail.get("persona_id") == selected_id:
                        selected_consumer[persona_type] = {
                            "persona_id": selected_id,
                            "persona_summary": detail.get("persona_summary", "")
                        }
                        break

    # Step 6: Generate insights for each selected consumer
    print(f"🔍 Generating insights for {len(selected_consumer)} selected consumers...")
    consumer_insights = {}

    for persona_type, consumer_data in selected_consumer.items():
        persona_summary = consumer_data.get("persona_summary", "")
        if persona_summary:
            print(f"  Generating insights for: {persona_type}")
            insights = generate_persona_insights(
                product_description=product_description,
                product_persona_name=persona_type,
                persona_summary=persona_summary
            )
            consumer_insights[persona_type] = {
                "persona_id": consumer_data.get("persona_id"),
                "insights": insights
            }

    print(f"✅ Generated insights for {len(consumer_insights)} consumers")

    # Build final response with only the requested keys
    result = {
        "would_buy_pie": would_buy_pie_counts,
        "yes_pie": yes_pie_counts,
        "age_distribution": age_distribution,
        "consumer_insights": consumer_insights,
        "demographics": {
            "target_age_ranges": age_ranges,
            "target_gender": gender
        }
    }

    return result

if __name__ == "__main__":
    sample_product_description = (
        "A high-quality, ergonomic office chair designed for maximum comfort "
        "and support during long working hours. Features adjustable height, "
        "lumbar support, and breathable mesh material."
    )
    query_result = run_query(sample_product_description)
    print("Final Query Result:")
    print(query_result)