"""pipeline/store_manager.py — Vectorstore registry + scoped retrieval.

All books are stored in ONE Chroma database. Retrieval is scoped using
Chroma's built-in metadata filters, so a query on "Class_6 / BGS / Chapter 2"
only searches that slice without needing a separate DB per book.

Registry (vectorstore/registry.json):
    Tracks every indexed book and its chapters so the UI / user can
    discover what is available without querying Chroma directly.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from settings.config import Config

log = logging.getLogger(__name__)

REGISTRY_PATH = Config.VECTORSTORE_DIR / "registry.json"


# --------------------------------------------------------------------------- #
# Registry helpers
# --------------------------------------------------------------------------- #

def _load_registry() -> dict:
    if REGISTRY_PATH.exists():
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"books": []}


def _save_registry(registry: dict) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)


def _book_key(class_number: str, book_name: str) -> str:
    return f"{class_number}__{book_name}"


def register_book(class_number: str, book_name: str, chapters: list[str], chunk_count: int) -> None:
    """Record a book in the registry after it has been indexed."""
    registry = _load_registry()
    key = _book_key(class_number, book_name)

    # Remove old entry if it exists (re-index case)
    registry["books"] = [b for b in registry["books"] if b["key"] != key]
    registry["books"].append({
        "key": key,
        "class_number": class_number,
        "book_name": book_name,
        "chapters": sorted(set(chapters)),
        "chunk_count": chunk_count,
    })
    _save_registry(registry)
    log.info("Registered: %s / %s  (%d chapters, %d chunks)", class_number, book_name, len(chapters), chunk_count)


def list_books() -> list[dict]:
    """Return all indexed books."""
    return _load_registry()["books"]


def list_chapters(class_number: str, book_name: str) -> list[str]:
    """Return chapters for a specific book."""
    key = _book_key(class_number, book_name)
    for book in _load_registry()["books"]:
        if book["key"] == key:
            return book["chapters"]
    return []


def is_indexed(class_number: str, book_name: str) -> bool:
    key = _book_key(class_number, book_name)
    return any(b["key"] == key for b in _load_registry()["books"])


# --------------------------------------------------------------------------- #
# Chroma filter builders
# --------------------------------------------------------------------------- #

def _make_filter(class_number: str | None, book_name: str | None, chapter: str | None) -> dict | None:
    """Build a Chroma `where` filter from the given scope."""
    conditions = []
    if class_number:
        conditions.append({"class_number": {"$eq": class_number}})
    if book_name:
        conditions.append({"book_name": {"$eq": book_name}})
    if chapter:
        conditions.append({"chapter": {"$eq": chapter}})

    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


# --------------------------------------------------------------------------- #
# Scoped retriever factory
# --------------------------------------------------------------------------- #

def get_scoped_retriever(
    vectorstore,
    chunks: list,
    class_number: str | None = None,
    book_name: str | None = None,
    chapter: str | None = None,
):
    """
    Return a hybrid retriever scoped to the requested book / chapter.

    Parameters
    ----------
    vectorstore : Chroma instance (full DB)
    chunks      : all chunks for the current scope (loaded from chunk cache)
    class_number: e.g. "class_6"
    book_name   : e.g. "bgs"
    chapter     : e.g. "মাছ চাষ"  (None = whole book)
    """
    from langchain_community.retrievers import BM25Retriever
    from langchain_classic.retrievers import EnsembleRetriever

    where = _make_filter(class_number, book_name, chapter)

    # Scope BM25 to matching chunks only
    scoped_chunks = _filter_chunks(chunks, class_number, book_name, chapter)
    if not scoped_chunks:
        log.warning("No chunks found for scope: class=%s book=%s chapter=%s", class_number, book_name, chapter)
        scoped_chunks = chunks  # fall back to all

    bm25 = BM25Retriever.from_documents(scoped_chunks)
    bm25.k = Config.BM25_TOP_K

    search_kwargs: dict[str, Any] = {"k": Config.DENSE_TOP_K}
    if where:
        search_kwargs["filter"] = where

    dense = vectorstore.as_retriever(search_kwargs=search_kwargs)

    return EnsembleRetriever(
        retrievers=[bm25, dense],
        weights=Config.HYBRID_WEIGHTS,
    )


def _filter_chunks(chunks: list, class_number: str | None, book_name: str | None, chapter: str | None) -> list:
    """Filter a chunk list by metadata fields."""
    result = chunks
    if class_number:
        result = [c for c in result if c.metadata.get("class_number") == class_number]
    if book_name:
        result = [c for c in result if c.metadata.get("book_name") == book_name]
    if chapter:
        result = [c for c in result if c.metadata.get("chapter") == chapter]
    return result
