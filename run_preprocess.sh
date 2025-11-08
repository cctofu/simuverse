#!/bin/bash
set -e

echo "🚀 Starting data pipeline..."

echo "📥 Running download_data.py..."
python download_data.py

echo "🧠 Running persona_generation.py..."
python persona_generation.py

echo "🔢 Running persona_embedding.py..."
python persona_embedding.py

echo "✅ All steps completed successfully!"
