"""Manual end-to-end check of the বই বন্ধু API. Run with the server up:

    python scripts/api_smoke_test.py
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from typing import Any

BASE = "http://127.0.0.1:8000"
CONTEXT = {
    "class_id": "class_5",
    "class_label": "৫ম শ্রেণি",
    "subject": "bangla",
    "subject_label": "বাংলা",
    "stream": None,
    "book": "class_5/bangla",
    "chapter": "বৈচিত্র্যময় বাংলাদেশ",
}


def post(path: str, payload: dict[str, Any] | None = None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else b"{}"
    request = urllib.request.Request(
        BASE + path, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        return urllib.request.urlopen(request, timeout=300)
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", "replace")
        raise SystemExit(f"POST {path} -> HTTP {error.code}\n{body}") from error


def get(path: str):
    return urllib.request.urlopen(BASE + path, timeout=60)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")

    health = json.loads(get("/api/health").read())
    print("health:", json.dumps(health, ensure_ascii=False))

    tree = json.loads(get("/api/tree").read())
    print("tree:", json.dumps(tree["counts"], ensure_ascii=False))

    with post("/api/threads", {"context": CONTEXT}) as response:
        thread = json.loads(response.read())
    thread_id = thread["thread_id"]
    print(f"created thread: {thread_id} · {thread['title']}")

    question = "বাংলাদেশের উৎসবগুলো কী কী?"
    started = time.time()
    events = 0
    answer: list[str] = []
    print(f"\nQ: {question}\n")
    with post(f"/api/threads/{thread_id}/chat", {"message": question, "context": CONTEXT}) as stream:
        for raw in stream:
            line = raw.decode("utf-8").strip()
            if not line:
                continue
            events += 1
            event = json.loads(line)
            kind = event["type"]
            if kind == "delta":
                answer.append(event["text"])
                sys.stdout.write(event["text"])
                sys.stdout.flush()
            elif kind == "sources":
                print(f"[sources: {len(event['sources'])} warning={event['warning']!r}]")
            elif kind == "status":
                print(f"[{event['stage']}] {event['message']}")
            elif kind == "done":
                print(f"\n[done thread={event['thread_id']}]")
            elif kind == "error":
                print(f"\n[ERROR] {event['message']}")
                return 1

    print(f"\n{events} events, {len(''.join(answer))} chars, {time.time() - started:.1f}s")

    detail = json.loads(get(f"/api/threads/{thread_id}").read())
    print(f"stored messages: {len(detail['messages'])}")
    groups = json.loads(get("/api/threads").read())
    print("sidebar groups:", [(group["label"], len(group["threads"])) for group in groups])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
