"""বই বন্ধু FastAPI application: chapter tree, thread persistence, streamed chat."""

# NOTE: no "from __future__ import annotations" here. FastAPI resolves endpoint
# annotations at import time, and PEP 563 string annotations break Pydantic models
# used as request bodies (they degrade to query parameters).

import json
import logging
import re
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


# These requests depend on the immediately preceding answer. Searching them as
# standalone textbook queries loses their referent (for example, "এটা সহজ করে
# বলো") and produces unrelated chunks. New factual questions still retrieve.
_FOLLOW_UP_PATTERNS = (
    r"^(?:আরও\s+)?(?:সহজ|সংক্ষেপে|বিস্তারিত)\s+(?:করে\s+)?(?:বল|বলো|বুঝ(?:িয়ে|িয়ে)|বোঝ(?:াও|াও)|লেখ)",
    r"^(?:আরও\s+)?(?:একটি\s+)?(?:উদাহরণ|mcq|ফ্ল্যাশকার্ড|নোট)",
    r"^(?:এটা|এটি|ওটা|ওইটা|উপরের(?:টা|টি)|আগের(?:টা|টি|উত্তর)|তা|এর)",
    r"^(?:কেন|কীভাবে|কিভাবে|তারপর|মানে)",
    r"^(?:please\s+)?(?:explain|simplify|summari[sz]e|expand|translate|give\s+(?:an\s+)?example)\b",
    r"^(?:this|that|it|they|why|how|what\s+does\s+(?:this|that|it)\s+mean)\b",
)


def _is_follow_up(question: str, history: list[dict[str, Any]]) -> bool:
    """Whether a question is explicitly referring to an earlier turn.

    This intentionally uses conservative markers instead of treating every
    later turn as a follow-up: a student can ask a new factual question in the
    same thread and should still receive fresh textbook retrieval.
    """
    if not history:
        return False
    normalized = " ".join(question.casefold().split())
    return any(re.match(pattern, normalized) for pattern in _FOLLOW_UP_PATTERNS)


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


def _retrieve(context: dict[str, Any], query: str) -> tuple[list[dict[str, Any]], str | None]:
    """Retrieve from the vector store for the selected chapter."""
    hits = search(context["book"], context["chapter"], query)
    return hits, None


def _event(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False) + "\n"


def _chat_stream(
    thread_id: str,
    context: dict[str, Any],
    question: str,
    history: list[dict[str, Any]],
) -> Iterator[str]:
    """Emit NDJSON events: status → delta* → done | error."""
    is_follow_up = _is_follow_up(question, history)
    hits: list[dict[str, Any]] = []
    if not is_follow_up:
        yield _event({"type": "status", "stage": "searching", "message": "পাঠ্যবই খোঁজা হচ্ছে..."})
        try:
            hits, _warning = _retrieve(context, question)
        except Exception as exc:  # noqa: BLE001 - surfaced to the client as an error event
            logger.exception("Retrieval failed")
            yield _event({"type": "error", "message": f"খোঁজার সময় সমস্যা হয়েছে: {exc}"})
            return

        if not hits:
            message = "কোনো প্রাসঙ্গিক অংশ পাওয়া যায়নি।"
            store.append_message(thread_id, {"role": "assistant", "content": message})
            yield _event({"type": "error", "message": message})
            return

    yield _event({"type": "status", "stage": "answering", "message": "উত্তর লেখা হচ্ছে..."})

    collected: list[str] = []
    try:
        for piece in stream_answer(question, hits, history=history):
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

    document = store.append_message(thread_id, {"role": "assistant", "content": answer})
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
        document = store.get(thread_id)
    except store.ThreadNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    context = _context_dict(payload.context)
    history = list(document.get("messages") or [])
    store.update_context(thread_id, context, payload.context.title)
    store.append_message(thread_id, {"role": "user", "content": payload.message})

    return StreamingResponse(
        _chat_stream(thread_id, context, payload.message, history),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
