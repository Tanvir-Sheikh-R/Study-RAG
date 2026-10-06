"""Thread persistence: one JSON file per thread under backend/data/threads/."""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.config import THREADS_DIR

_lock = threading.RLock()
_ID_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"


class ThreadNotFound(LookupError):
    """Raised when a thread id has no stored file."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_thread_id() -> str:
    return uuid.uuid4().hex[:12]


def _path(thread_id: str) -> Path:
    if not thread_id or any(char not in _ID_ALPHABET for char in thread_id):
        raise ThreadNotFound(f"Invalid thread id: {thread_id!r}")
    return THREADS_DIR / f"{thread_id}.json"


def _write(document: dict[str, Any]) -> None:
    THREADS_DIR.mkdir(parents=True, exist_ok=True)
    target = _path(document["thread_id"])
    temporary = target.with_suffix(f".{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    os.replace(temporary, target)


def create(context: dict[str, Any], title: str) -> dict[str, Any]:
    stamp = _now_iso()
    document = {
        "thread_id": new_thread_id(),
        "title": title.strip() or "নতুন চ্যাট",
        "context": context,
        "messages": [],
        "created_at": stamp,
        "updated_at": stamp,
    }
    with _lock:
        _write(document)
    return document


def get(thread_id: str) -> dict[str, Any]:
    with _lock:
        path = _path(thread_id)
        if not path.exists():
            raise ThreadNotFound(f"No thread with id {thread_id}")
        return json.loads(path.read_text(encoding="utf-8"))


def list_all() -> list[dict[str, Any]]:
    """Newest-updated first, with a preview of the last message for the sidebar."""
    with _lock:
        if not THREADS_DIR.is_dir():
            return []
        documents: list[dict[str, Any]] = []
        for path in THREADS_DIR.glob("*.json"):
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            documents.append(document)

    documents.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
    summaries: list[dict[str, Any]] = []
    for document in documents:
        messages = document.get("messages") or []
        preview = ""
        if messages:
            preview = str(messages[-1].get("content", ""))[:120]
        summaries.append(
            {
                "thread_id": document["thread_id"],
                "title": document.get("title", "নতুন চ্যাট"),
                "context": document.get("context") or {},
                "message_count": len(messages),
                "preview": preview,
                "created_at": document.get("created_at"),
                "updated_at": document.get("updated_at"),
            }
        )
    return summaries


def append_message(thread_id: str, message: dict[str, Any]) -> dict[str, Any]:
    with _lock:
        document = get(thread_id)
        message.setdefault("created_at", _now_iso())
        document["messages"].append(message)
        document["updated_at"] = _now_iso()
        _write(document)
        return document


def update_context(thread_id: str, context: dict[str, Any], title: str | None = None) -> dict[str, Any]:
    with _lock:
        document = get(thread_id)
        document["context"] = context
        if title:
            document["title"] = title.strip() or document["title"]
        document["updated_at"] = _now_iso()
        _write(document)
        return document


def delete(thread_id: str) -> None:
    with _lock:
        path = _path(thread_id)
        if not path.exists():
            raise ThreadNotFound(f"No thread with id {thread_id}")
        path.unlink()


def _relative_bucket(updated_at: str | None) -> str:
    if not updated_at:
        return "আগে"
    try:
        stamp = datetime.fromisoformat(updated_at)
    except ValueError:
        return "আগে"
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    age_days = (time.time() - stamp.timestamp()) / 86400
    if age_days < 1:
        return "আজ"
    if age_days < 2:
        return "গতকাল"
    if age_days < 7:
        return "৭ দিন আগে"
    if age_days < 30:
        return "৩০ দিন আগে"
    return "পুরোনো"


def grouped() -> list[dict[str, Any]]:
    """Threads bucketed for the sidebar's relative-date headers."""
    groups: list[dict[str, Any]] = []
    for summary in list_all():
        bucket = _relative_bucket(summary.get("updated_at"))
        if not groups or groups[-1]["label"] != bucket:
            groups.append({"label": bucket, "threads": []})
        groups[-1]["threads"].append(summary)
    return groups
