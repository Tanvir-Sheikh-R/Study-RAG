# """pipeline package — Bangla NCTB textbook RAG pipeline."""

# from pipeline.ocr import run_ocr
# from pipeline.metadata import load_chapter_index, get_page_metadata
# from pipeline.chunker import (
#     pages_to_documents,
#     merge_by_chapter,
#     build_splitter,
#     chunk_cached,
#     add_passage_prefix,
# )
# from pipeline.vectorstore import load_embeddings, load_or_build_vectorstore, add_to_vectorstore
# from pipeline.retriever import build_hybrid_retriever, build_answer_chain, answer, search
# from pipeline.store_manager import (
#     list_books,
#     list_chapters,
#     is_indexed,
#     register_book,
#     get_scoped_retriever,
# )

# __all__ = [
#     # OCR
#     "run_ocr",
#     # Metadata
#     "load_chapter_index", "get_page_metadata",
#     # Chunking
#     "pages_to_documents", "merge_by_chapter", "build_splitter", "chunk_cached", "add_passage_prefix",
#     # Vectorstore
#     "load_embeddings", "load_or_build_vectorstore", "add_to_vectorstore",
#     # Retrieval
#     "build_hybrid_retriever", "build_answer_chain", "answer", "search",
#     # Store manager
#     "list_books", "list_chapters", "is_indexed", "register_book", "get_scoped_retriever",
# ]
