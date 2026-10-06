"""Paths and constants shared by the বই বন্ধু backend.

Reads the artifacts produced by pipeline/pdf_to_document_cleanV2.ipynb
(chapters.json, ocr_cache/, embedding_cache/, model_cache/) and never writes to them.
"""

from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent

# Loads GUI, GROQ, OpenRouter and DeepSeek keys used by the answer chain.
load_dotenv(ROOT / ".env")

CHAPTERS_INDEX = ROOT / "chapters.json"
EMBEDDING_CACHE = ROOT / "embedding_cache"
OCR_CACHE = ROOT / "ocr_cache"
MODEL_CACHE = ROOT / "model_cache"

# Threads live outside the read-only experiment caches.
DATA_DIR = ROOT / "backend" / "data"
THREADS_DIR = DATA_DIR / "threads"

EMBEDDING_MODEL = "intfloat/multilingual-e5-large"
E5_QUERY_PREFIX = "query: "
E5_PASSAGE_PREFIX = "passage: "

# Notebook defaults: text_splitter chunk_size=1500 / overlap=350, and k=5 for both retrievers.
HYBRID_K = 5
HYBRID_WEIGHTS = (0.4, 0.6)  # (bm25, dense)

# "deepseek-flash" exists but returns empty content; deepseek-chat is the working model.
LLM_MODEL = "deepseek-chat"
LLM_TEMPERATURE = 0.2
LLM_MAX_TOKENS = 2048

TOC_KEYWORDS = ("সূচিপত্র", "সুচিপত্র", "বিষয়সূচি", "CONTENTS", "contents")

CORS_ORIGINS = ("http://localhost:3000", "http://127.0.0.1:3000")
