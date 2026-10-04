"""pipeline/vectorstore.py — Stage 4: embeddings + Chroma vectorstore."""
from __future__ import annotations

import logging
import os
import time

from langchain_core.documents import Document

from settings.config import Config

log = logging.getLogger(__name__)


def load_embeddings():
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    from langchain_huggingface import HuggingFaceEmbeddings

    start = time.time()
    embeddings = HuggingFaceEmbeddings(
        model_name=Config.EMBEDDING_MODEL,
        cache_folder=str(Config.EMBEDDING_CACHE_FOLDER),
        encode_kwargs={"normalize_embeddings": True},
    )
    log.info("Embedding model loaded in %.2fs", time.time() - start)
    return embeddings


def load_or_build_vectorstore(chunks: list[Document], embeddings, rebuild: bool = False):
    """Load the existing shared vectorstore, or create it from chunks."""
    from langchain_chroma import Chroma

    persist_dir = str(Config.VECTORSTORE_DIR)
    already_exists = os.path.exists(persist_dir) and os.listdir(persist_dir)

    if already_exists and not rebuild:
        log.info("Loading existing vectorstore: %s", persist_dir)
        return Chroma(
            persist_directory=persist_dir,
            embedding_function=embeddings,
            collection_name=Config.COLLECTION_NAME,
        )

    if chunks:
        log.info("Building vectorstore from %d chunks", len(chunks))
        return Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=persist_dir,
            collection_name=Config.COLLECTION_NAME,
        )

    # Empty store (will be populated incrementally via add_to_vectorstore)
    log.info("Creating empty vectorstore at %s", persist_dir)
    return Chroma(
        persist_directory=persist_dir,
        embedding_function=embeddings,
        collection_name=Config.COLLECTION_NAME,
    )


def add_to_vectorstore(vectorstore, chunks: list[Document]) -> None:
    """Incrementally add one book's chunks — safe to call after each book."""
    if chunks:
        vectorstore.add_documents(chunks)
        log.info("Added %d chunks to vectorstore", len(chunks))
