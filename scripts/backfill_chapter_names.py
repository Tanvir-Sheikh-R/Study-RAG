"""Backfill missing chapter_name.txt / chunks.json sidecars in the hashed cache.

The notebook's migration (pipeline/pdf_to_document_cleanV2.ipynb) writes each chapter
as a hashed folder md5(name)[:10] holding index.faiss/index.pkl + bm25.pkl, plus a
chapter_name.txt sidecar and a copy of chunks.json. 57 hashed folders ended up with
only the FAISS/BM25 files, so their chapters are not discoverable by name.

This script rebuilds the missing sidecars from the still-present legacy long-name
folders (vectors.npy + chunks.json), which the hash key maps to 1:1. It only ever
adds files that are missing — never overwrites an existing sidecar — so it is safe to
re-run and never touches the notebook.

Usage:
    python scripts/backfill_chapter_names.py
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EMBED_CACHE = ROOT / "embedding_cache"


def chapter_hash(name: str) -> str:
    return hashlib.md5(name.encode("utf-8")).hexdigest()[:10]


class _LoadOnlyEmbeddings:
    """Placeholder so FAISS.load_local can deserialize; no query embedding is needed."""

    def embed_documents(self, texts):
        return [[0.0]] * len(texts)

    def embed_query(self, text):
        return [0.0]


def rebuild_chunks_from_faiss(hashed_dir: Path) -> bool:
    """Reconstruct chunks.json from the FAISS docstore (for dirs with no legacy copy)."""
    try:
        from langchain_community.vectorstores import FAISS

        vectorstore = FAISS.load_local(
            str(hashed_dir), _LoadOnlyEmbeddings(), allow_dangerous_deserialization=True
        )
    except Exception as error:  # noqa: BLE001 - report and move on, this is a best-effort fill
        print(f"  ! could not load FAISS for {hashed_dir.name}: {error}")
        return False

    ids = list(vectorstore.index_to_docstore_id.values())
    chunks = []
    for doc_id in ids:
        document = vectorstore.docstore.search(doc_id)
        chunks.append({"text": document.page_content, "meta": dict(document.metadata)})
    (hashed_dir / "chunks.json").write_text(
        json.dumps(chunks, ensure_ascii=False), encoding="utf-8"
    )
    return True


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    old_dirs = [path.parent for path in EMBED_CACHE.rglob("vectors.npy")]
    filled_name = filled_chunks = rebuilt = skipped = 0

    for old_dir in old_dirs:
        name = old_dir.name
        hashed_dir = old_dir.parent / chapter_hash(name)
        if not hashed_dir.is_dir() or not (hashed_dir / "index.faiss").exists():
            continue

        if not (hashed_dir / "chapter_name.txt").exists():
            (hashed_dir / "chapter_name.txt").write_text(name, encoding="utf-8")
            filled_name += 1

        if not (hashed_dir / "chunks.json").exists():
            shutil.copy2(old_dir / "chunks.json", hashed_dir / "chunks.json")
            filled_chunks += 1

        if (hashed_dir / "chapter_name.txt").exists() and (hashed_dir / "chunks.json").exists():
            skipped += 1

    # Any hashed dir still without chunks.json has no legacy sibling: rebuild from FAISS.
    for index_file in EMBED_CACHE.rglob("index.faiss"):
        hashed_dir = index_file.parent
        if (hashed_dir / "chunks.json").exists():
            continue
        if rebuild_chunks_from_faiss(hashed_dir):
            rebuilt += 1

    still_missing = [
        path.parent
        for path in EMBED_CACHE.rglob("index.faiss")
        if not (path.parent / "chapter_name.txt").exists() or not (path.parent / "chunks.json").exists()
    ]
    print(f"wrote chapter_name.txt   : {filled_name}")
    print(f"copied chunks.json       : {filled_chunks}")
    print(f"rebuilt from FAISS       : {rebuilt}")
    print(f"already complete         : {skipped}")
    print(f"hashed dirs still incomplete: {len(still_missing)}")
    for missing in still_missing[:20]:
        print("  ", missing.parent.parent.name, "/", missing.name)
    return 1 if still_missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
