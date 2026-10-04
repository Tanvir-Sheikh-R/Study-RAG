"""pipeline/chunker.py — Stage 3: pages → Documents, chapter merge, text splitting."""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from settings.config import Config
from metadata import get_page_metadata

log = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Pages → LangChain Documents
# --------------------------------------------------------------------------- #

def pages_to_documents(pages: list[dict], chapter_index: dict) -> list[Document]:
    documents = []
    skipped = 0

    for item in pages:
        item = dict(item)  # don't mutate cached data
        content = item.pop("page_content", "")
        page = item.get("page_number")

        if page is None or page < 0:
            continue  # pre-TOC / cover pages — skip

        metas = get_page_metadata(chapter_index, item.get("class_number"), item.get("book_name"), page)
        if not metas:
            skipped += 1

        documents.append(Document(page_content=content, metadata={**item, **metas}))

    if skipped:
        log.warning("%d page(s) had no chapter metadata", skipped)
    log.info("%d page-level documents built", len(documents))
    return documents


# --------------------------------------------------------------------------- #
# Merge pages by chapter (reduces chunk fragmentation)
# --------------------------------------------------------------------------- #

def merge_by_chapter(documents: list[Document]) -> list[Document]:
    grouped: dict[str, list[Document]] = defaultdict(list)
    for doc in documents:
        chapter = doc.metadata.get("chapter", "বই তথ্য")
        grouped[chapter].append(doc)

    merged = []
    for chapter, docs in grouped.items():
        docs = sorted(docs, key=lambda d: d.metadata.get("page_number", 0))
        page_nums = [d.metadata.get("page_number") for d in docs]
        merged.append(Document(
            page_content="\n\n".join(d.page_content for d in docs),
            metadata={
                "chapter": chapter,
                "book_name": docs[0].metadata.get("book_name"),
                "class_number": docs[0].metadata.get("class_number"),
                "page_start": min(page_nums),
                "page_end": max(page_nums),
            },
        ))

    log.info("%d chapter-level documents after merge", len(merged))
    return merged


# --------------------------------------------------------------------------- #
# Text splitting + e5 prefix
# --------------------------------------------------------------------------- #

def build_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=Config.CHUNK_SIZE,
        chunk_overlap=Config.CHUNK_OVERLAP,
        length_function=len,
        is_separator_regex=False,
        separators=Config.CHUNK_SEPARATORS,
    )


def add_passage_prefix(chunks: list[Document], prefix: str = Config.E5_PASSAGE_PREFIX) -> list[Document]:
    """e5 models need 'passage: ' prefix on indexed text for best retrieval."""
    for chunk in chunks:
        if not chunk.page_content.startswith(prefix):
            chunk.page_content = prefix + chunk.page_content
    return chunks


# --------------------------------------------------------------------------- #
# Cached chunking
# --------------------------------------------------------------------------- #

def chunk_cached(book_id: str, chapter_docs: list[Document], splitter, force: bool = False) -> list[Document]:
    cache_path = Config.CHUNK_CACHE_DIR / f"{book_id}_chunks.json"

    if not force and cache_path.exists():
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        log.info("Chunk cache hit: %s", book_id)
        return [Document(page_content=d["page_content"], metadata=d["metadata"]) for d in data]

    chunks = splitter.split_documents(chapter_docs)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump([{"page_content": c.page_content, "metadata": c.metadata} for c in chunks], f, ensure_ascii=False, indent=2)

    return chunks
