"""বই বন্ধু RAG pipeline: chapter index, cached embeddings, hybrid retrieval, answer chain."""

from backend.rag.answer import build_chain, format_context, stream_answer
from backend.rag.chapters import (
    build_tree,
    cached_book_paths,
    chapter_label,
    class_label,
    known_classes,
    subject_label,
)
from backend.rag.embeddings import model_info, warm_up
from backend.rag.retriever import search

__all__ = [
    "build_chain",
    "format_context",
    "stream_answer",
    "build_tree",
    "cached_book_paths",
    "chapter_label",
    "class_label",
    "known_classes",
    "subject_label",
    "model_info",
    "warm_up",
    "search",
]

