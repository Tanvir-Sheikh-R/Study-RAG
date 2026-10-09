"""Hybrid BM25 + dense retrieval over a single chapter's cached embeddings.

Follows the retrieval cell of pipeline/pdf_to_document_cleanV2.ipynb: each chapter
folder holds a FAISS index (index.faiss/index.pkl) plus its chunks (chunks.json), so
nothing is re-embedded at query time. BM25 is rebuilt from chunks.json here because
the notebook pickles its own in-notebook tokenizer object, which is not importable
outside that module. Legacy long-name folders with vectors.npy are still supported.
"""

from __future__ import annotations

import json
import re
import threading
from functools import lru_cache
from typing import Any

from langchain_community.retrievers import BM25Retriever
from langchain_community.vectorstores import FAISS
from langchain_classic.retrievers import EnsembleRetriever
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from backend.config import HYBRID_K, HYBRID_WEIGHTS
from backend.rag.chapters import find_chapter_dir
from backend.rag.embeddings import encode_query

_build_lock = threading.Lock()

_BANGLA_PUNCTUATION = re.compile(r"[।,;:!?\"'()\[\]{}\-—–“”‘’]")


class E5QueryEmbeddings(Embeddings):
    """Query-side embeddings for FAISS.

    The dense index is loaded from disk, so only query embedding is needed; FAISS also
    probes its embedding callable directly, hence __call__.
    """

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("The dense index is loaded from the cached FAISS store.")

    def embed_query(self, text: str) -> list[float]:
        return encode_query(text).tolist()

    def __call__(self, text: str) -> list[float]:
        return self.embed_query(text)


def _bn_tokenize(text: str) -> list[str]:
    return _BANGLA_PUNCTUATION.sub(" ", text).split()


def _load_documents(directory) -> list[Document]:
    """Reconstruct LangChain documents from a cache folder's chunks.json."""
    chunks = json.loads((directory / "chunks.json").read_text(encoding="utf-8"))
    return [
        Document(page_content=item["text"], metadata=item.get("meta") or {}) for item in chunks
    ]


def _load_dense(directory, documents: list[Document]):
    """Load the dense retriever: FAISS index from disk, else rebuild from vectors.npy."""
    if (directory / "index.faiss").exists():
        vectorstore = FAISS.load_local(
            str(directory), E5QueryEmbeddings(), allow_dangerous_deserialization=True
        )
    elif (directory / "vectors.npy").exists():
        import numpy as np

        vectors = np.load(directory / "vectors.npy")
        vectorstore = FAISS.from_embeddings(
            text_embeddings=list(zip([doc.page_content for doc in documents], vectors)),
            embedding=E5QueryEmbeddings(),
            metadatas=[doc.metadata for doc in documents],
        )
    else:
        raise FileNotFoundError(f"No FAISS index or vectors in {directory}")
    return vectorstore.as_retriever(search_kwargs={"k": HYBRID_K})


@lru_cache(maxsize=32)
def _build(book: str, chapter: str):
    directory = find_chapter_dir(book, chapter)
    if directory is None:
        raise FileNotFoundError(f"No cached embeddings for {book} / {chapter}")

    documents = _load_documents(directory)
    dense = _load_dense(directory, documents)

    bm25 = BM25Retriever.from_documents(documents, preprocess_func=_bn_tokenize)
    bm25.k = HYBRID_K

    return EnsembleRetriever(retrievers=[bm25, dense], weights=list(HYBRID_WEIGHTS))


def get_retriever(book: str, chapter: str) -> EnsembleRetriever:
    with _build_lock:
        return _build(book, chapter)


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
