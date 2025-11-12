#!/bin/bash
echo "🚀 Cleaning repository of cache and system files..."

# Remove all __pycache__, .pytest_cache, .ipynb_checkpoints, etc.
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null
find . -type d -name ".ipynb_checkpoints" -exec rm -rf {} + 2>/dev/null
find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null

# Remove Other files
find . -type f -name ".DS_Store" -delete 2>/dev/null
find . -type f -name ".claude" -delete 2>/dev/null

echo "✅ Cleanup complete."
