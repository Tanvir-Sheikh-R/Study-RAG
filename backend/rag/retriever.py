"""Hybrid BM25 + dense retrieval over a single chapter's cached embeddings.

Mirrors retrieval cell of pipeline/pdf_to_document_cleanV2.ipynb: the dense half is a
FAISS index built from the vectors already stored in embedding_cache, so nothing is
re-embedded at query time. Results are cached per chapter because the BM25 index and
FAISS store are built from disk once.
"""

from __future__ import annotations

import json
import re
import threading
from functools import lru_cache
from typing import Any

import numpy as np
from langchain_community.retrievers import BM25Retriever
from langchain_community.vectorstores import FAISS
from langchain_classic.retrievers import EnsembleRetriever
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from backend.config import HYBRID_K, HYBRID_WEIGHTS
from backend.rag.chapters import find_chapter_dir
from backend.rag.embeddings import encode_query, model_info

_build_lock = threading.Lock()

_BANGLA_PUNCTUATION = re.compile(r"[।,;:!?\"'()\[\]{}\-—–“”‘’]")


class E5QueryEmbeddings(Embeddings):
    """Query-side embeddings for FAISS.

    The dense index is always built from vectors.npy, so only query embedding is
    implemented; FAISS also probes its embedding callable directly, hence __call__.
    """

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("The dense index is built from cached vectors.")

    def embed_query(self, text: str) -> list[float]:
        return encode_query(text).tolist()

    def __call__(self, text: str) -> list[float]:
        return self.embed_query(text)


def _bn_tokenize(text: str) -> list[str]:
    return _BANGLA_PUNCTUATION.sub(" ", text).split()


@lru_cache(maxsize=32)
def _build(book: str, chapter: str):
    directory = find_chapter_dir(book, chapter)
    if directory is None:
        raise FileNotFoundError(f"No cached embeddings for {book} / {chapter}")

    chunks = json.loads((directory / "chunks.json").read_text(encoding="utf-8"))
    vectors = np.load(directory / "vectors.npy")
    if len(chunks) != len(vectors):
        raise ValueError(
            f"Cache mismatch in {directory.name}: {len(chunks)} chunks vs {len(vectors)} vectors"
        )

    documents = [
        Document(page_content=item["text"], metadata=item.get("meta") or {}) for item in chunks
    ]
    vectorstore = FAISS.from_embeddings(
        text_embeddings=list(zip([doc.page_content for doc in documents], vectors)),
        embedding=E5QueryEmbeddings(),
        metadatas=[doc.metadata for doc in documents],
    )

    dense = vectorstore.as_retriever(search_kwargs={"k": HYBRID_K})
    bm25 = BM25Retriever.from_documents(documents, preprocess_func=_bn_tokenize)
    bm25.k = HYBRID_K

    return EnsembleRetriever(retrievers=[bm25, dense], weights=list(HYBRID_WEIGHTS))


def get_retriever(book: str, chapter: str) -> EnsembleRetriever:
    with _build_lock:
        return _build(book, chapter)


def is_cached(book: str, chapter: str) -> bool:
    return find_chapter_dir(book, chapter) is not None


def search_across_book(book: str, query: str, k: int = HYBRID_K) -> list[dict[str, Any]]:
    """Fallback when the requested chapter has no cache: rank every cached chapter."""
    from backend.rag.chapters import cached_chapter_dirs

    merged: dict[str, dict[str, Any]] = {}
    for chapter in sorted(cached_chapter_dirs(book)):
        try:
            hits = search(book, chapter, query, k=k)
        except (FileNotFoundError, ValueError):
            continue
        for rank, hit in enumerate(hits):
            text = hit["text"]
            if text in merged:
                merged[text]["rank"] += 1 / (rank + 1)
            else:
                merged[text] = {**hit, "rank": 1 / (rank + 1)}

    ordered = sorted(merged.values(), key=lambda item: item["rank"], reverse=True)
    for item in ordered:
        item.pop("rank", None)
    return ordered[:k]


def search(book: str, chapter: str, query: str, k: int = HYBRID_K) -> list[dict[str, Any]]:
    documents = get_retriever(book, chapter).invoke(query)[:k]
    hits: list[dict[str, Any]] = []
    for document in documents:
        metadata = document.metadata
        hits.append(
            {
                "text": document.page_content,
                "chapter": metadata.get("chapter"),
                "part": metadata.get("part"),
                "writer_name": metadata.get("writer_name"),
                "page_start": metadata.get("page_start"),
                "page_end": metadata.get("page_end"),
            }
        )
    return hits


def cache_summary(book: str, chapter: str) -> dict[str, Any]:
    directory = find_chapter_dir(book, chapter)
    if directory is None:
        return {"cached": False}
    vectors = np.load(directory / "vectors.npy")
    return {
        "cached": True,
        "directory": str(directory),
        "chunks": int(vectors.shape[0]),
        "dimension": int(vectors.shape[1]),
        "embedding_dimension": model_info()["dimension"],
    }
