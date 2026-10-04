"""
pdf_to_document.py — CLI entry point and pipeline orchestrator.

Usage:
    python pdf_to_document.py --pdf "pdf/Class_6/BGS.pdf" --query "মাছ চাষের পদক্ষেপ কি?"
    python pdf_to_document.py --pdf "pdf/Class_6/BGS.pdf" --ocr-engine gpu --rebuild-index
    python pdf_to_document.py --pdf "pdf/Class_6/BGS.pdf" --force-ocr
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from dotenv import load_dotenv

from ocr import run_ocr
from metadata import load_chapter_index
from chunker import pages_to_documents, merge_by_chapter, build_splitter, chunk_cached, add_passage_prefix
from vectorstore import load_embeddings, load_or_build_vectorstore
from retriever import build_hybrid_retriever, build_answer_chain, answer


load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("pdf_to_document")


def process_book(pdf_path: Path, chapter_index: dict, splitter, ocr_engine: str, force: bool) -> list:
    """Full per-book pipeline: OCR → metadata → merge → chunk (all cached)."""
    pages = run_ocr(pdf_path, engine=ocr_engine, force=force)
    documents = pages_to_documents(pages, chapter_index)
    chapter_docs = merge_by_chapter(documents)
    chunks = chunk_cached(pdf_path.stem.lower(), chapter_docs, splitter, force=force)
    return add_passage_prefix(chunks)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bangla textbook RAG pipeline")
    parser.add_argument("--pdf", type=Path, required=True, help="Path to the textbook PDF")
    parser.add_argument("--query", type=str, default=None, help="Question to ask after indexing")
    parser.add_argument("--ocr-engine", choices=["cpu", "gpu"], default="cpu")
    parser.add_argument("--force-ocr", action="store_true", help="Ignore cache and re-run OCR")
    parser.add_argument("--rebuild-index", action="store_true", help="Rebuild the vectorstore from scratch")
    args = parser.parse_args()

    chapter_index = load_chapter_index()
    splitter = build_splitter()

    chunks = process_book(args.pdf, chapter_index, splitter, args.ocr_engine, args.force_ocr)

    embeddings = load_embeddings()
    vectorstore = load_or_build_vectorstore(chunks, embeddings, rebuild=args.rebuild_index)
    retriever = build_hybrid_retriever(chunks, vectorstore)

    if args.query:
        chain = build_answer_chain()
        print(answer(retriever, chain, args.query))


if __name__ == "__main__":
    main()