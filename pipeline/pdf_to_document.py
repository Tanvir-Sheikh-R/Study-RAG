from __future__ import annotations

import argparse
import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Any

import pytesseract
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pdf2image import convert_from_path
from PIL import ImageOps
from rapidfuzz import fuzz
from pypdf import PdfReader
from tqdm import tqdm


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOC_KEYWORDS = ("সূচিপত্র", "সুচিপত্র", "বিষয়সূচি")
DEFAULT_MATCH_THRESHOLD = 80

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
    is_separator_regex=False,
    separators=["\n\n", "\n", "।", " ", ""],
)


def load_chapters(chapters_path: Path, class_no: int, subject_name: str) -> list[dict[str, Any]]:
    with chapters_path.open("r", encoding="utf-8") as file:
        index = json.load(file)

    class_key = f"class_{class_no}"
    books = index["all_books"][class_key]
    subject_key = subject_name.casefold()
    if subject_key == "math":
        subject_key = "mathematics"
    if subject_key not in books:
        available = ", ".join(books)
        raise ValueError(f"No index for {class_key}/{subject_name}. Available: {available}")

    chapters = books[subject_key]
    if not chapters:
        raise ValueError(f"No chapters found for {class_key}/{subject_key}")
    return sorted(chapters, key=lambda chapter: chapter["chapter_number"])


def find_pdf_path(project_root: Path, class_no: int, subject_name: str) -> Path:
    class_pdf_dir = project_root / "pdf" / f"Class_{class_no}"
    subject_stem = "Math" if subject_name.casefold() in {"math", "mathematics"} else subject_name
    pdf_path = next(
        (
            candidate
            for candidate in class_pdf_dir.glob("*.pdf")
            if candidate.stem.casefold() == subject_stem.casefold()
        ),
        class_pdf_dir / f"{subject_stem}.pdf",
    )
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF not found for class {class_no}, subject {subject_name}: {pdf_path}")
    return pdf_path


def ocr_pdf_to_pages(
    pdf_path: Path,
    poppler_path: str | None = None,
    lang: str = "ben",
    dpi: int = 300,
) -> list[dict[str, Any]]:
    convert_options: dict[str, Any] = {"dpi": dpi}
    if poppler_path:
        convert_options["poppler_path"] = poppler_path

    page_count = len(PdfReader(str(pdf_path)).pages)
    pages = []
    batch_size = 8
    with tqdm(total=page_count, desc="OCR processing") as progress:
        for first_page in range(1, page_count + 1, batch_size):
            last_page = min(first_page + batch_size - 1, page_count)
            images = convert_from_path(
                str(pdf_path),
                first_page=first_page,
                last_page=last_page,
                **convert_options,
            )
            for page_index, image in enumerate(images, start=first_page):
                image = ImageOps.autocontrast(image.convert("L"))
                text = pytesseract.image_to_string(image, lang=lang)
                pages.append({"pdf_page_index": page_index, "text": text})
                progress.update(1)
            images.clear()
    return pages


def load_or_ocr_pages(
                    pdf_path: Path,
                    cache_path: Path,
                    poppler_path: str | None = None,
                    lang: str = "ben",
                    force_ocr: bool = False,
                    ) -> list[dict[str, Any]]:
    
    stat = pdf_path.stat()
    signature = {"size": stat.st_size, "modified_ns": stat.st_mtime_ns}
    if cache_path.exists() and not force_ocr:
        with cache_path.open("r", encoding="utf-8") as file:
            cache = json.load(file)
        if cache.get("source_pdf") == str(pdf_path.resolve()) and cache.get("signature") == signature:
            print(f"Using cached page OCR: {cache_path}")
            return cache["pages"]

    pages = ocr_pdf_to_pages(pdf_path, poppler_path=poppler_path, lang=lang)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open("w", encoding="utf-8") as file:
        json.dump(
            {"source_pdf": str(pdf_path.resolve()), "signature": signature, "pages": pages},
            file,
            ensure_ascii=False,
        )
    return pages


def find_toc_pages(
    pages: list[dict[str, Any]], keywords: tuple[str, ...] = TOC_KEYWORDS
) -> set[int]:
    return {
        page["pdf_page_index"]
        for page in pages
        if any(keyword in page["text"] for keyword in keywords)
    }


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return re.sub(r"[\W_]+", "", normalized, flags=re.UNICODE)


def page_title_score(title: str, page_text: str) -> int:
    normalized_title = normalize_text(title)
    lines = [line.strip() for line in page_text.splitlines() if line.strip()]
    candidates = []
    for window_size in range(1, min(3, len(lines)) + 1):
        candidates.extend(
            " ".join(lines[start : start + window_size])
            for start in range(len(lines) - window_size + 1)
        )

    best_score = 0
    for candidate in candidates:
        normalized_candidate = normalize_text(candidate)
        if not normalized_candidate:
            continue
        score = fuzz.ratio(normalized_title, normalized_candidate)
        candidate_length = len(normalized_candidate)
        if (
            len(normalized_title) >= 8
            and len(normalized_title) * 3 // 4 <= candidate_length <= len(normalized_title) * 2
        ):
            score = max(score, fuzz.partial_ratio(normalized_title, normalized_candidate))
        best_score = max(best_score, round(score))
    return best_score


def locate_chapter_starts(
    pages: list[dict[str, Any]],
    chapters: list[dict[str, Any]],
    threshold: int = DEFAULT_MATCH_THRESHOLD,
) -> tuple[dict[int, dict[str, Any]], set[int]]:
    toc_pages = find_toc_pages(pages)
    scores: dict[tuple[int, int], int] = {}
    for page in pages:
        for chapter_index, chapter in enumerate(chapters):
            scores[(page["pdf_page_index"], chapter_index)] = page_title_score(
                chapter["chapter_name"], page["text"]
            )

    # TOC pages may continue without repeating the TOC heading.
    listing_pages = {
        page["pdf_page_index"]
        for page in pages
        if sum(
            scores[(page["pdf_page_index"], chapter_index)] >= threshold
            for chapter_index in range(len(chapters))
        ) >= 3
    }
    toc_pages.update(listing_pages)
    for toc_page in tuple(toc_pages):
        for neighbor in (toc_page - 1, toc_page + 1):
            matched_titles = sum(
                scores.get((neighbor, chapter_index), 0) >= threshold
                for chapter_index in range(len(chapters))
            )
            if matched_titles >= 2:
                toc_pages.add(neighbor)

    starts: dict[int, dict[str, Any]] = {}
    previous_start = 0
    for chapter_index, chapter in enumerate(chapters):
        for page in pages:
            page_index = page["pdf_page_index"]
            if page_index in toc_pages or page_index <= previous_start:
                continue
            if scores[(page_index, chapter_index)] >= threshold:
                starts[page_index] = chapter
                previous_start = page_index
                break
    return starts, toc_pages


def build_page_map(
    pages: list[dict[str, Any]], starts: dict[int, dict[str, Any]]
) -> dict[int, tuple[int | None, str, int | None]]:
    ordered_starts = sorted(starts.items())
    page_map = {}
    active_chapter: dict[str, Any] | None = None
    next_start = 0
    for page in pages:
        page_index = page["pdf_page_index"]
        while next_start < len(ordered_starts) and ordered_starts[next_start][0] <= page_index:
            active_chapter = ordered_starts[next_start][1]
            next_start += 1
        if active_chapter is None:
            page_map[page_index] = (None, "Unknown", None)
        else:
            page_map[page_index] = (
                active_chapter["chapter_number"],
                active_chapter["chapter_name"],
                active_chapter.get("starting_page"),
            )
    return page_map


def pages_to_documents(
    pages: list[dict[str, Any]],
    page_map: dict[int, tuple[int | None, str, int | None]],
    source: str,
    class_no: int,
    subject_name: str,
) -> list[Document]:
    documents = []
    for page in pages:
        page_index = page["pdf_page_index"]
        chapter_number, chapter_name, printed_starting_page = page_map[page_index]
        metadata = {
            "source": source,
            "pdf_page_index": page_index,
            "chapter_number": chapter_number,
            "chapter_name": chapter_name,
            "chapter_starting_page": printed_starting_page,
            "class_number": class_no,
            "subject": subject_name,
        }
        for paragraph in re.split(r"\n\s*\n", page["text"]):
            if paragraph.strip():
                documents.append(Document(page_content=paragraph.strip(), metadata=metadata.copy()))
    return documents


def save_pages_as_text(pages: list[dict[str, Any]], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8") as file:
        for page in pages:
            file.write(f"[PDF_PAGE_{page['pdf_page_index']}]\n")
            file.write(page["text"].rstrip())
            file.write("\n\n")


def save_documents(documents: list[Document], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8") as file:
        for document in documents:
            json.dump(
                {"page_content": document.page_content, "metadata": document.metadata},
                file,
                ensure_ascii=False,
            )
            file.write("\n")


def build_documents(
    class_no: int = 5,
    subject_name: str = "Bangla",
    project_root: Path = PROJECT_ROOT,
    match_threshold: int = DEFAULT_MATCH_THRESHOLD,
    poppler_path: str | None = None,
    force_ocr: bool = False,
) -> list[Document]:
    pdf_path = find_pdf_path(project_root, class_no, subject_name)
    chapters_path = project_root / "chapters.json"
    output_dir = project_root / "extracted_text" / f"Class_{class_no}"
    cache_path = output_dir / f"{pdf_path.stem}_pages.json"
    text_path = output_dir / f"{pdf_path.stem}_ocr.txt"
    documents_path = output_dir / f"{pdf_path.stem}_documents.jsonl"

    chapters = load_chapters(chapters_path, class_no, subject_name)
    pages = load_or_ocr_pages(
        pdf_path, cache_path, poppler_path=poppler_path, force_ocr=force_ocr
    )
    starts, toc_pages = locate_chapter_starts(pages, chapters, threshold=match_threshold)
    page_map = build_page_map(pages, starts)
    source = pdf_path.relative_to(project_root).as_posix()
    page_documents = pages_to_documents(pages, page_map, source, class_no, subject_name)
    chunks = text_splitter.split_documents(page_documents)
    output_dir.mkdir(parents=True, exist_ok=True)
    save_pages_as_text(pages, text_path)
    save_documents(chunks, documents_path)

    print(f"TOC pages: {sorted(toc_pages)}")
    print(f"Matched chapter starts: {len(starts)}/{len(chapters)}")
    print(f"Page documents: {len(page_documents)}; chunks: {len(chunks)}")
    print(f"Page OCR text saved: {text_path}")
    print(f"Chunk documents saved: {documents_path}")
    return chunks


def main() -> None:
    # parser = argparse.ArgumentParser(description="OCR a textbook PDF and create chapter-aware chunks.")
    # parser.add_argument("--class-no", type=int, default=5)
    # parser.add_argument("--subject", default="Bangla")
    # parser.add_argument("--match-threshold", type=int, default=DEFAULT_MATCH_THRESHOLD)
    # parser.add_argument("--poppler-path", default=os.getenv("POPPLER_PATH"))
    # parser.add_argument("--force-ocr", action="store_true")
    # args = parser.parse_args()
    # build_documents(
    #     class_no=args.class_no,
    #     subject_name=args.subject,
    #     match_threshold=args.match_threshold,
    #     poppler_path=args.poppler_path,
    #     force_ocr=args.force_ocr,
    # )
    print(PROJECT_ROOT)


if __name__ == "__main__":
    main()