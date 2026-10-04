from pathlib import Path


class Config:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    print("hi ",PROJECT_ROOT)
    POPPLER_PATH = r"C:\poppler\Library\bin"
    TESSERACT_LANG = "ben"

    CHAPTERS_INDEX_PATH = PROJECT_ROOT / "chapters.json"
    OCR_CACHE_DIR = PROJECT_ROOT / "cache/ocr_cache"
    CHUNK_CACHE_DIR = PROJECT_ROOT / "cache/chunk_cache"

    TOC_KEYWORDS = ("সূচিপত্র", "সুচিপত্র", "বিষয়সূচি", "CONTENTS", "contents")

    CHUNK_SIZE = 1500
    CHUNK_OVERLAP = 300
    CHUNK_SEPARATORS = ["\n\n\n", "\n\n", "\n", "।", " ", ""]

    EMBEDDING_MODEL = "intfloat/multilingual-e5-large"
    EMBEDDING_CACHE_FOLDER = PROJECT_ROOT / "model_cache"
    E5_QUERY_PREFIX = "query: "
    E5_PASSAGE_PREFIX = "passage: "

    VECTORSTORE_DIR = PROJECT_ROOT / "books_db"
    COLLECTION_NAME = "nctb_books"

    BM25_TOP_K = 5
    DENSE_TOP_K = 5
    HYBRID_WEIGHTS = [0.4, 0.6]  # [bm25, dense]

    LLM_MODEL = "deepseek-chat"
    LLM_TEMPERATURE = 0.2
    LLM_MAX_TOKENS = 2048

    ANSWER_PROMPT = """You are a Bangladeshi teacher helping students learn from their textbooks.
                    Maintain professionalism and be polite and helpful.

                    Student's question: {query}

                    Use the following textbook content as your primary source:
                    {content}

                    You may use your own knowledge, but keep that to a minimum and prefer the textbook content.
                    If nothing relevant is found in the content, reply: "এই প্রশ্নটি পাঠ্যবইয়ে উল্লেখ নেই।"
                    You may then optionally add a short answer from your own knowledge."""
