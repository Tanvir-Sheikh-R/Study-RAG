"""বই বন্ধু FastAPI application: chapter tree, thread persistence, streamed chat."""

# NOTE: no "from __future__ import annotations" here. FastAPI resolves endpoint
# annotations at import time, and PEP 563 string annotations break Pydantic models
# used as request bodies (they degrade to query parameters).

import json
import logging
from contextlib import asynccontextmanager
from typing import Any, Iterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend import store
from backend.config import CORS_ORIGINS, LLM_MODEL
from backend.rag import (
    build_tree,
    cached_book_paths,
    model_info,
    search,
    search_across_book,
    stream_answer,
    warm_up,
)
from backend.rag.chapters import all_book_paths
from backend.schemas import (
    ChatStart,
    HealthOut,
    MessageOut,
    ThreadContextUpdate,
    ThreadCreate,
    ThreadDetail,
    ThreadGroup,
    ThreadSummary,
)

logger = logging.getLogger("boibondhu")

SNIPPET_LIMIT = 400


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the embedding model during startup so the first question is not slow."""
    try:
        logger.info("Warming up embedding model: %s", model_info())
    except Exception:  # pragma: no cover - startup must not hard-fail on model issues
        logger.exception("Embedding model warm-up failed; it will retry on first query")
    yield


app = FastAPI(title="বই বন্ধু API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(CORS_ORIGINS),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _context_dict(context: Any) -> dict[str, Any]:
    return context.model_dump()


def _to_thread_summary(document: dict[str, Any]) -> ThreadSummary:
    messages = document.get("messages") or []
    return ThreadSummary(
        thread_id=document["thread_id"],
        title=document.get("title", "নতুন চ্যাট"),
        context=document.get("context") or {},
        message_count=len(messages),
        preview=str(messages[-1].get("content", ""))[:120] if messages else "",
        created_at=document.get("created_at", ""),
        updated_at=document.get("updated_at", ""),
    )


def _to_thread_detail(document: dict[str, Any]) -> ThreadDetail:
    return ThreadDetail(
        thread_id=document["thread_id"],
        title=document.get("title", "নতুন চ্যাট"),
        context=document.get("context") or {},
        messages=[MessageOut(**message) for message in document.get("messages") or []],
        created_at=document.get("created_at", ""),
        updated_at=document.get("updated_at", ""),
    )


def _source_payload(hit: dict[str, Any]) -> dict[str, Any]:
    text = str(hit.get("text", ""))
    return {
        "chapter": hit.get("chapter"),
        "part": hit.get("part"),
        "writer_name": hit.get("writer_name"),
        "page_start": hit.get("page_start"),
        "page_end": hit.get("page_end"),
        "snippet": text[:SNIPPET_LIMIT],
    }


def _retrieve(context: dict[str, Any], query: str) -> tuple[list[dict[str, Any]], str | None]:
    """Chapter-scoped retrieval, falling back to the whole book when uncached."""
    book = context["book"]
    chapter = context["chapter"]
    try:
        hits = search(book, chapter, query)
    except (FileNotFoundError, ValueError):
        hits = []
    if hits:
        return hits, None

    fallback = search_across_book(book, query)
    if fallback:
        return fallback, "এই অধ্যায়ের জন্য সূচি তৈরি হয়নি — পুরো বই থেকে খোঁজা হয়েছে।"
    return [], "এই বইটির জন্য এখনো সূচি (embedding) তৈরি হয়নি।"


def _event(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False) + "\n"


def _chat_stream(thread_id: str, context: dict[str, Any], question: str) -> Iterator[str]:
    """Emit NDJSON events: status → sources → delta* → done | error."""
    yield _event({"type": "status", "stage": "searching", "message": "পাঠ্যবই খোঁজা হচ্ছে..."})

    try:
        hits, warning = _retrieve(context, question)
    except Exception as exc:  # noqa: BLE001 - surfaced to the client as an error event
        logger.exception("Retrieval failed")
        yield _event({"type": "error", "message": f"খোঁজার সময় সমস্যা হয়েছে: {exc}"})
        return

    if not hits:
        message = warning or "কোনো প্রাসঙ্গিক অংশ পাওয়া যায়নি।"
        store.append_message(thread_id, {"role": "assistant", "content": message, "sources": []})
        yield _event({"type": "error", "message": message})
        return

    sources = [_source_payload(hit) for hit in hits]
    yield _event({"type": "sources", "sources": sources, "warning": warning})
    yield _event({"type": "status", "stage": "answering", "message": "উত্তর লেখা হচ্ছে..."})

    collected: list[str] = []
    try:
        for piece in stream_answer(question, hits):
            collected.append(piece)
            yield _event({"type": "delta", "text": piece})
    except Exception as exc:  # noqa: BLE001 - surfaced to the client as an error event
        logger.exception("Answer generation failed")
        yield _event({"type": "error", "message": f"উত্তর তৈরি করতে সমস্যা হয়েছে: {exc}"})
        return

    answer = "".join(collected).strip()
    if not answer:
        yield _event({"type": "error", "message": "মডেল কোনো উত্তর দেয়নি। আবার চেষ্টা করুন।"})
        return

    document = store.append_message(
        thread_id, {"role": "assistant", "content": answer, "sources": sources}
    )
    yield _event(
        {
            "type": "done",
            "thread_id": thread_id,
            "title": document["title"],
            "updated_at": document["updated_at"],
        }
    )


@app.get("/api/health", response_model=HealthOut)
def health() -> HealthOut:
    try:
        info = model_info()
    except Exception:  # noqa: BLE001 - report degraded state instead of failing
        logger.exception("Model info unavailable")
        info = {"model": "unavailable", "device": "unknown", "dimension": 0}
    return HealthOut(
        status="ok",
        embedding_model=str(info["model"]),
        device=str(info["device"]),
        dimension=int(info["dimension"]),
        indexed_books=len(cached_book_paths()),
        named_books=len(all_book_paths()),
        llm_model=LLM_MODEL,
    )


@app.post("/api/health/warmup", response_model=HealthOut)
def warmup() -> HealthOut:
    try:
        warm_up()
    except Exception as exc:  # noqa: BLE001 - surfaced as a 503 for the UI
        logger.exception("Warm-up failed")
        raise HTTPException(status_code=503, detail=f"Embedding model load failed: {exc}") from exc
    return health()


@app.get("/api/tree")
def tree() -> dict[str, Any]:
    classes = build_tree()
    return {
        "classes": classes,
        "counts": {
            "classes": len(classes),
            "subjects": sum(len(item["subjects"]) for item in classes),
            "chapters": sum(
                len(subject["chapters"])
                for item in classes
                for subject in item["subjects"]
            ),
            "indexed_books": len(cached_book_paths()),
        },
    }


@app.get("/api/threads", response_model=list[ThreadGroup])
def list_threads() -> list[ThreadGroup]:
    return [ThreadGroup(**group) for group in store.grouped()]


@app.post("/api/threads", response_model=ThreadDetail)
def create_thread(payload: ThreadCreate) -> ThreadDetail:
    document = store.create(_context_dict(payload.context), payload.context.title)
    return _to_thread_detail(document)


@app.get("/api/threads/{thread_id}", response_model=ThreadDetail)
def get_thread(thread_id: str) -> ThreadDetail:
    try:
        document = store.get(thread_id)
    except store.ThreadNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_thread_detail(document)


@app.put("/api/threads/{thread_id}/context", response_model=ThreadDetail)
def update_thread_context(thread_id: str, payload: ThreadContextUpdate) -> ThreadDetail:
    try:
        document = store.update_context(
            thread_id, _context_dict(payload.context), payload.context.title
        )
    except store.ThreadNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_thread_detail(document)


@app.delete("/api/threads/{thread_id}", status_code=204)
def delete_thread(thread_id: str) -> None:
    try:
        store.delete(thread_id)
    except store.ThreadNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/threads/{thread_id}/chat")
def chat(thread_id: str, payload: ChatStart) -> StreamingResponse:
    try:
        store.get(thread_id)
    except store.ThreadNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    context = _context_dict(payload.context)
    store.update_context(thread_id, context, payload.context.title)
    store.append_message(thread_id, {"role": "user", "content": payload.message})

    return StreamingResponse(
        _chat_stream(thread_id, context, payload.message),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
