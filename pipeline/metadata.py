"""pipeline/metadata.py — Stage 2: chapters.json TOC index lookup."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from settings.config import Config

log = logging.getLogger(__name__)


def load_chapter_index(path: Path = Config.CHAPTERS_INDEX_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_page_metadata(index: dict, class_num: str | None, book_name: str | None, page: int | None) -> dict[str, Any]:
    """Return {chapter, part, writer_name} for a given page number."""
    if class_num is None or book_name is None or page is None or page < 0:
        return {}

    book_section = index.get("all_books", {}).get(class_num, {}).get(book_name)
    if not book_section:
        return {}

    metas: dict[str, Any] = {}
    for chapter in book_section:
        start = chapter.get("starting_page")
        if start is None or start > page:
            continue

        if chapter.get("sub_chapters"):
            for sub in chapter["sub_chapters"]:
                sub_start = sub.get("starting_page")
                if sub_start is not None and sub_start <= page:
                    metas["part"] = chapter.get("chapter_name")
                    metas["chapter"] = sub.get("sub_chapter_name")
                    if sub.get("writer_name"):
                        metas["writer_name"] = sub["writer_name"]
                    else:
                        metas.pop("writer_name", None)
        else:
            metas["chapter"] = chapter.get("chapter_name")
            metas.pop("part", None)
            metas.pop("writer_name", None)

    return metas
