"""chapters.json access: the page → chapter index, plus the UI chapter tree.

The published artifact keeps everything under a single "all_books" key:

    all_books.class_5..class_8 : {subject: [chapter, ...]}
    all_books.class_9_10       : {stream: {subject: [chapter, ...]}}

A chapter carries chapter_number, chapter_name, starting_page and an optional
sub_chapters list whose entries carry sub_chapter_name, writer_name and starting_page.

Every path elsewhere in the app names a book as "class_id/book", so this module owns
the single implementation of that lookup plus the book path spoken by embedding_cache.
"""

from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.config import CHAPTERS_INDEX, EMBEDDING_CACHE

CLASS_ORDER = ("class_5", "class_6", "class_7", "class_8", "class_9_10")

CLASS_LABELS = {
    "class_5": "৫ম শ্রেণি",
    "class_6": "৬ষ্ঠ শ্রেণি",
    "class_7": "৭ম শ্রেণি",
    "class_8": "৮ম শ্রেণি",
    "class_9_10": "৯ম-১০ম শ্রেণি",
}

STREAM_LABELS = {
    "general": "সাধারণ",
    "arts": "মানবিক",
    "commerce": "ব্যবসায় শিক্ষা",
    "science": "বিজ্ঞান",
}

SUBJECT_LABELS = {
    "bangla": "বাংলা",
    "bangla_bekoron": "বাংলা ব্যাকরণ",
    "bangla_bakoron": "বাংলা ব্যাকরণ",
    "bangla_grammar": "বাংলা ব্যাকরণ",
    "bangla_sahitto": "বাংলা সাহিত্য",
    "bangla_sohopath": "বাংলা সহপাঠ",
    "charupath": "চারুপাঠ",
    "anandopah": "আনন্দপাঠ",
    "anandapatha": "আনন্দপাঠ",
    "anondopath": "আনন্দপাঠ",
    "sahitto_konika": "সাহিত্য কণিকা",
    "english": "ইংরেজি",
    "english_grammar": "ইংরেজি ব্যাকরণ",
    "english_gerammar": "ইংরেজি ব্যাকরণ",
    "mathematics": "গণিত",
    "math": "গণিত",
    "higher_math": "উচ্চতর গণিত",
    "science": "বিজ্ঞান",
    "physics": "পদার্থবিজ্ঞান",
    "chemistry": "রসায়ন",
    "biology": "জীববিজ্ঞান",
    "bgs": "বাংলাদেশ ও বিশ্বপরিচয়",
    "history": "ইতিহাস",
    "bhugol": "ভূগোল",
    "civics": "পৌরনীতি ও নাগরিকতা",
    "economics": "অর্থনীতি",
    "accounting": "হিসাববিজ্ঞান",
    "business_entrepreneurship": "ব্যবসায় উদ্যোগ",
    "finance_banking": "ফিন্যান্স ও ব্যাংকিং",
    "agriculture": "কৃষিশিক্ষা",
    "krishi": "কৃষিশিক্ষা",
    "home_science": "গৃহবিজ্ঞান",
    "ict": "তথ্য ও যোগাযোগ প্রযুক্তি",
    "career": "কর্মমুখী শিক্ষা",
    "kormo_o_jibon": "কর্ম ও জীবনমুখী শিক্ষা",
    "kormo_o_jibonmukhi_sikkha": "কর্ম ও জীবনমুখী শিক্ষা",
    "physical_education": "শারীরিক শিক্ষা",
    "sharirik_sikha": "শারীরিক শিক্ষা",
    "songit": "সংগীত",
    "songeet": "সংগীত",
    "songgit": "সংগীত",
    "arts_crafts": "চারু ও কারুকলা",
    "art_craft": "চারু ও কারুকলা",
    "songskrito": "সংস্কৃত",
}

_UNKNOWN_CHAPTER = "শিরোনামহীন"


@lru_cache(maxsize=1)
def load_index() -> dict[str, Any]:
    with CHAPTERS_INDEX.open(encoding="utf-8") as handle:
        return json.load(handle)["all_books"]


def known_classes() -> list[str]:
    index = load_index()
    ordered = [cls for cls in CLASS_ORDER if cls in index]
    return ordered + sorted(set(index) - set(ordered))


@lru_cache(maxsize=64)
def streams_of(class_id: str) -> tuple[str, ...]:
    """Streams for a class, or () when subjects sit directly under the class."""
    node = load_index().get(class_id) or {}
    return tuple(key for key, value in node.items() if isinstance(value, dict))


@lru_cache(maxsize=64)
def subjects_of(class_id: str, stream: str | None = None) -> tuple[str, ...]:
    node = load_index().get(class_id) or {}
    if stream:
        return tuple((node.get(stream) or {}).keys())
    return tuple(key for key, value in node.items() if isinstance(value, list))


def resolve_scope(class_id: str, stream: str | None, subject: str) -> dict[str, Any] | None:
    """Return the chapter list for a (class, stream, subject), or None if unknown."""
    node = load_index().get(class_id)
    if not isinstance(node, dict):
        return None

    if stream:
        target = (node.get(stream) or {}).get(subject)
        if isinstance(target, list):
            return {"stream": stream, "subject": subject, "chapters": target}
        return None

    target = node.get(subject)
    if isinstance(target, list):
        return {"stream": None, "subject": subject, "chapters": target}

    # No stream was given, but this class nests subjects under streams: search them.
    for stream_key, stream_node in node.items():
        if isinstance(stream_node, dict) and isinstance(stream_node.get(subject), list):
            return {"stream": stream_key, "subject": subject, "chapters": stream_node[subject]}
    return None


def chapters_of(class_id: str, stream: str | None, subject: str) -> list[dict[str, Any]]:
    scope = resolve_scope(class_id, stream, subject)
    return list(scope["chapters"]) if scope else []


def subject_label(subject: str) -> str:
    return SUBJECT_LABELS.get(subject, subject.replace("_", " ").strip().title())


def class_label(class_id: str) -> str:
    return CLASS_LABELS.get(class_id, class_id.replace("_", " ").title())


def book_path(class_id: str, subject: str, stream: str | None = None) -> str:
    """The path key used by embedding_cache directories: class/subject or class/stream/subject.

    class_9_10 nests a stream between class and subject, which is exactly how the PDFs
    are laid out on disk (pdf/Class_9_10/General/English.pdf).
    """
    return f"{class_id}/{stream}/{subject}" if stream else f"{class_id}/{subject}"


def normalize_name(name: str) -> str:
    """Unicode-normalise and collapse whitespace so names compare reliably."""
    normalized = unicodedata.normalize("NFC", name)
    return re.sub(r"\s+", " ", normalized).strip()


def chapter_dir_name(chapter: str) -> str:
    """Windows-safe directory name, matching the notebook's sanitiser."""
    cleaned = "".join("_" if char in '<>:"/\\|?*' else char for char in normalize_name(chapter))
    return cleaned.strip().rstrip(".") or _UNKNOWN_CHAPTER


def _loose(name: str) -> str:
    """Fold away whitespace, underscores, case and composing forms for matching."""
    normalized = unicodedata.normalize("NFD", name).lower()
    return re.sub(r"[\s_\-]+", "", normalized)


def book_has_vectors(book: str) -> bool:
    """True when a book's cache dir holds at least one embedded chapter."""
    directory = EMBEDDING_CACHE.joinpath(*book.split("/"))
    if not directory.is_dir():
        return False
    return any((child / "vectors.npy").exists() for child in directory.iterdir() if child.is_dir())


def cached_book_paths() -> set[str]:
    """Every class/book (or class/stream/book) path that has embedded chapters."""
    return {book for book in all_book_paths() if book_has_vectors(book)}


def all_book_paths() -> list[str]:
    """Every book path named by the index, whether or not it has cached vectors."""
    paths: list[str] = []
    for class_id in known_classes():
        streams = streams_of(class_id)
        if streams:
            for stream in streams:
                paths.extend(
                    book_path(class_id, subject, stream)
                    for subject in subjects_of(class_id, stream)
                )
        else:
            paths.extend(book_path(class_id, subject) for subject in subjects_of(class_id))
    return paths


def cached_chapter_dirs(book: str) -> set[str]:
    directory = EMBEDDING_CACHE.joinpath(*book.split("/"))
    if not directory.is_dir():
        return set()
    return {child.name for child in directory.iterdir() if (child / "vectors.npy").exists()}


def find_chapter_dir(book: str, chapter: str) -> Path | None:
    """Locate a chapter's cache dir, tolerating sanitiser/typo drift in names."""
    directory = EMBEDDING_CACHE.joinpath(*book.split("/"))
    if not directory.is_dir():
        return None

    wanted = chapter_dir_name(chapter)
    candidates = [
        directory / wanted,
        directory / normalize_name(chapter),
        directory / wanted.replace("_", " "),
        directory / wanted.replace(" ", "_"),
        directory / wanted.replace("_", "/"),
    ]
    for candidate in candidates:
        if (candidate / "vectors.npy").exists():
            return candidate

    squashed = _loose(wanted)
    for child in directory.iterdir():
        if _loose(child.name) == squashed and (child / "vectors.npy").exists():
            return child
    return None


def chapter_label(chapter: dict[str, Any]) -> str:
    name = str(chapter.get("chapter_name") or "").strip() or _UNKNOWN_CHAPTER
    number = chapter.get("chapter_number")
    return f"{number}. {name}" if number else name


def build_tree() -> list[dict[str, Any]]:
    """Class → subjects (with stream when nested) → chapters, for the selection modal."""
    tree: list[dict[str, Any]] = []
    cached = cached_book_paths()

    for class_id in known_classes():
        streams = streams_of(class_id)
        subjects: list[dict[str, Any]] = []

        def add_subject(subject: str, stream: str | None) -> None:
            chapters = chapters_of(class_id, stream, subject)
            if not chapters:
                return
            book = book_path(class_id, subject, stream)
            subjects.append(
                {
                    "subject": subject,
                    "stream": stream,
                    "label": subject_label(subject),
                    "book": book,
                    "indexed": book in cached,
                    "chapters": [
                        {
                            "name": chapter_label(chapter),
                            "chapter_name": str(chapter.get("chapter_name") or _UNKNOWN_CHAPTER),
                            "number": chapter.get("chapter_number"),
                            "starting_page": chapter.get("starting_page"),
                            "sub_chapters": [
                                {
                                    "name": str(sub.get("sub_chapter_name") or _UNKNOWN_CHAPTER),
                                    "number": sub.get("sub_chapter_number"),
                                    "starting_page": sub.get("starting_page"),
                                    "writer_name": sub.get("writer_name"),
                                }
                                for sub in (chapter.get("sub_chapters") or [])
                            ],
                        }
                        for chapter in chapters
                    ],
                }
            )

        if streams:
            for stream in streams:
                for subject in subjects_of(class_id, stream):
                    add_subject(subject, stream)
        else:
            for subject in subjects_of(class_id):
                add_subject(subject, None)

        if subjects:
            tree.append(
                {
                    "class_id": class_id,
                    "label": class_label(class_id),
                    "nested": bool(streams),
                    "subjects": subjects,
                }
            )
    return tree
