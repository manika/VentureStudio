from pathlib import Path
import os

# Data directory — one level up from the project folder (VentureStudio/data/)
# Can be overridden with the DATA_DIR environment variable.
DATA_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).parent.parent / "data"))

# Ollama settings
MODEL_NAME = "qwen2.5:3b"
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")

# Storage
STORAGE_DIR = Path(__file__).parent / "storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Simple vector store config (TF-IDF placeholder for Stage 1)
VEC_STORE_PATH = STORAGE_DIR / "tfidf_store.pkl"

# App settings
APP_TITLE = "Venture Studio AI Advisor"

# Privacy / access control
ALLOW_RAW_PARENT_DOCS_TO_LLM = False

# Data directories
PARENT_COMPANY_RAW_DIR = DATA_DIR / "parent_company_raw"
PARENT_COMPANY_REDACTED_DIR = DATA_DIR / "parent_company_redacted"
SHARED_TEMPLATES_DIR = DATA_DIR / "shared_templates"

# Storage sub-directories
CHROMA_DIR = STORAGE_DIR / "chroma_db"
CACHE_DIR = STORAGE_DIR / "cache"

# Outputs
OUTPUTS_DIR = Path(__file__).parent / "outputs"

# Graph paths
KNOWLEDGE_GRAPH_PATH = STORAGE_DIR / "knowledge_graph.graphml"
KNOWLEDGE_GRAPH_JSON = STORAGE_DIR / "knowledge_graph.json"
EXTRACTION_AUDIT_LOG = STORAGE_DIR / "extraction_audit_log.csv"

# Limits
MAX_INPUT_CHARS = 8000
MAX_RETRIEVED_CHUNKS = 3
MAX_CHUNK_CHARS = 800
MAX_GRAPH_NODES = 8
MAX_GRAPH_RELATIONSHIPS = 12
MAX_COMPANY_PROFILE_CHARS = 1000
MAX_OUTPUT_TOKENS = 800
SAVE_PROMPT_LOGS = True
DEBUG_PROMPTS = False

# Chunking
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150

# Ensure directories exist
for _d in [PARENT_COMPANY_RAW_DIR, PARENT_COMPANY_REDACTED_DIR, SHARED_TEMPLATES_DIR,
           CHROMA_DIR, CACHE_DIR, OUTPUTS_DIR,
           OUTPUTS_DIR / "generalized_templates",
           OUTPUTS_DIR / "advisor_reports",
           OUTPUTS_DIR / "prompt_logs"]:
    _d.mkdir(parents=True, exist_ok=True)
