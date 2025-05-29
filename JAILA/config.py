"""
Konfigurationsfil for JAILA.
Indeholder miljøvariabler og konstanter til brug i systemet.
"""
import os
from dotenv import load_dotenv

# Indlæs miljøvariabler
load_dotenv()
openai_api_key = os.environ.get("OPENAI_API_KEY")
weaviate_url = os.environ.get("WEAVIATE_URL", "http://localhost:8080")

# Definer klassens navne og metadata felter
CLASS_NAME = "LegalDocument"
METADATA_FIELDS = ["chunk_id", "title", "law_number", "paragraph", "stk", "nr", "heading", "summary"]

# Standard konfiguration for LLM
DEFAULT_MODEL = "gpt-4o-2024-08-06"
DEFAULT_TEMPERATURE = 0.0
