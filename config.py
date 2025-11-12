import os
from dotenv import load_dotenv
load_dotenv()

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = "text-embedding-3-large"
SUMMARY_MODEL = "gpt-4o-mini"  

# Preprocess Configuration
MAX_WORKERS = 5  
SAVE_INTERVAL = 25

# Database Configuration
DATABASE_PATH = "data/Twin-2K-500_final.json"

# Backend Configuration
TOP_K = 200
CHAT_MODEL = "gpt-5-nano-2025-08-07"