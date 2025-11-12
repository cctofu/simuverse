#!/bin/bash
set -e

echo "🚀 Starting data pipeline..."

$CHECKPOINT_1="data/Twin-2K-500_persona_structured.json"
$CHECKPOINT_2="data/Twin-2K-500_with_summaries.json"
$CHECKPOINT_3="data/Twin-2K-500_with_embeddings.json"
$OUTPUT_FILE="data/Twin-2K-500_final.json"

echo "📥 Running download_data.py..."
python download_data.py --output_dir "$CHECKPOINT_1"

echo "🧠 Running persona_generation.py..."
python persona_generation.py --input_file "$CHECKPOINT_1" --output_file "$CHECKPOINT_2"

echo "🔢 Running persona_embedding.py..."
python persona_embedding.py --input_file "$CHECKPOINT_2" --output_file "$CHECKPOINT_3"

echo "🔍 Running cluster_embedding.py...
python cluster_embedding.py --input_file "$CHECKPOINT_3" --output_file "$OUTPUT_FILE"

echo "✅ All steps completed successfully!"
