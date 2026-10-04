"""pipeline/bulk_index.py — Index every PDF in the pdf/ folder into the vectorstore.

Run this once (or after adding new books) to build/update the index:

    python -m pipeline.bulk_index
    python -m pipeline.bulk_index --ocr-engine gpu
    python -m pipeline.bulk_index --force          # re-OCR + re-chunk everything
    python -m pipeline.bulk_index --skip-indexed   # skip already-indexed books (default)

The script is crash-safe: every book's OCR and chunks are cached to disk,
so a failure midway never loses already-finished work.
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from dotenv import load_dotenv

from settings.config import Config
from ocr import run_ocr
from metadata import load_chapter_index
from chunker import pages_to_documents, merge_by_chapter, build_splitter, chunk_cached, add_passage_prefix
from vectorstore import load_embeddings, load_or_build_vectorstore, add_to_vectorstore
from store_manager import register_book, is_indexed

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("bulk_index")

PDF_ROOT = Config.PROJECT_ROOT / "pdf"


def discover_pdfs(pdf_root: Path) -> list[Path]:
    """Recursively collect all .pdf files under pdf_root."""
    return sorted(pdf_root.rglob("*.pdf"))


def process_one_book(
    pdf_path: Path,
    chapter_index: dict,
    splitter,
    embeddings,
    vectorstore,
    ocr_engine: str,
    force: bool,
) -> int:
    """OCR → metadata → merge → chunk → embed one book. Returns chunk count."""
    pages = run_ocr(pdf_path, engine=ocr_engine, force=force)
    documents = pages_to_documents(pages, chapter_index)
    chapter_docs = merge_by_chapter(documents)

    book_id = pdf_path.stem.lower()
    chunks = chunk_cached(book_id, chapter_docs, splitter, force=force)
    chunks = add_passage_prefix(chunks)

    # Add to the shared vectorstore
    add_to_vectorstore(vectorstore, chunks)

    # Record in registry
    chapters = list({c.metadata.get("chapter", "") for c in chunks if c.metadata.get("chapter")})
    class_number = pdf_path.parent.name.lower()
    register_book(class_number, book_id, chapters, len(chunks))

    return len(chunks)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bulk-index all NCTB textbook PDFs")
    parser.add_argument("--ocr-engine", choices=["cpu", "gpu"], default="cpu")
    parser.add_argument("--force", action="store_true", help="Re-process even if already indexed")
    parser.add_argument("--skip-indexed", action="store_true", default=True,
                        help="Skip books already in the registry (default: True)")
    args = parser.parse_args()

    pdfs = discover_pdfs(PDF_ROOT)
    log.info("Found %d PDF(s) under %s", len(pdfs), PDF_ROOT)

    chapter_index = load_chapter_index()
    splitter = build_splitter()
    embeddings = load_embeddings()

    # Load or create the shared vectorstore once
    vectorstore = load_or_build_vectorstore([], embeddings, rebuild=args.force)

    total_chunks = 0
    skipped = 0
    failed = []

    for i, pdf_path in enumerate(pdfs, 1):
        class_number = pdf_path.parent.name.lower()
        book_id = pdf_path.stem.lower()
        log.info("[%d/%d] %s / %s", i, len(pdfs), class_number, book_id)

        if args.skip_indexed and not args.force and is_indexed(class_number, book_id):
            log.info("  → already indexed, skipping")
            skipped += 1
            continue

        try:
            n = process_one_book(pdf_path, chapter_index, splitter, embeddings, vectorstore, args.ocr_engine, args.force)
            total_chunks += n
            log.info("  → done (%d chunks)", n)
        except Exception as e:
            log.error("  → FAILED: %s", e)
            failed.append(str(pdf_path))

    log.info("=" * 60)
    log.info("Indexed: %d books | Skipped: %d | Failed: %d", len(pdfs) - skipped - len(failed), skipped, len(failed))
    log.info("Total chunks added: %d", total_chunks)
    if failed:
        log.warning("Failed books:\n  %s", "\n  ".join(failed))


if __name__ == "__main__":
    main()
