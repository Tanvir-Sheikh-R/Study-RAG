"""Drive headless Chrome over the DevTools protocol to verify the বই বন্ধু UI.

Usage (Chrome must already be started with --remote-debugging-port=9333):

    python scripts/ui_preview.py <thread_id>

Captures .preview/*.png and prints the assertion results for each interaction:
selection popup, empty state, sending a question, and thread restore.
"""

from __future__ import annotations

import asyncio
import base64
import json
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

import websockets

DEBUG_URL = "http://127.0.0.1:9333"
PREVIEW_DIR = Path(__file__).resolve().parent.parent / ".preview"
APP_URL = "http://127.0.0.1:3000"


class DevTools:
    def __init__(self, socket: Any) -> None:
        self._socket = socket
        self._counter = 0

    async def send(self, method: str, **params: Any) -> dict[str, Any]:
        self._counter += 1
        message_id = self._counter
        await self._socket.send(json.dumps({"id": message_id, "method": method, "params": params}))
        while True:
            raw = json.loads(await self._socket.recv())
            if raw.get("id") == message_id:
                if "error" in raw:
                    raise RuntimeError(f"{method} failed: {raw['error']}")
                return raw.get("result", {})

    async def eval(self, expression: str) -> Any:
        result = await self.send(
            "Runtime.evaluate",
            expression=expression,
            awaitPromise=True,
            returnByValue=True,
        )
        return result.get("result", {}).get("value")

    async def goto(self, url: str) -> None:
        await self.send("Page.navigate", url=url)

    async def shot(self, name: str) -> Path:
        result = await self.send("Page.captureScreenshot", format="png")
        path = PREVIEW_DIR / f"{name}.png"
        path.write_bytes(base64.b64decode(result["data"]))
        return path

    async def wait_for(self, expression: str, timeout: float = 45.0) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if await self.eval(expression):
                return True
            await asyncio.sleep(0.5)
        return False


def page_websocket_url() -> str:
    with urllib.request.urlopen(f"{DEBUG_URL}/json/list", timeout=10) as response:
        targets = json.loads(response.read())
    for target in targets:
        if target.get("type") == "page":
            return str(target["webSocketDebuggerUrl"])
    raise SystemExit("No page target; is Chrome running with --remote-debugging-port=9333?")


async def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    PREVIEW_DIR.mkdir(exist_ok=True)
    thread_id = sys.argv[1] if len(sys.argv) > 1 else None
    checks: list[tuple[str, bool, str]] = []

    def check(label: str, ok: bool, detail: str = "") -> None:
        checks.append((label, ok, detail))
        print(f"{'PASS' if ok else 'FAIL'}  {label}{f' — {detail}' if detail else ''}")

    async with websockets.connect(page_websocket_url(), max_size=64 * 1024 * 1024) as socket:
        devtools = DevTools(socket)
        await devtools.send("Page.enable")
        await devtools.send("Runtime.enable")

        # 1. First load: blocking selection popup.
        await devtools.goto(APP_URL)
        ready = await devtools.wait_for("!!document.querySelector('[role=dialog]')")
        check("selection popup opens on load", ready)
        await devtools.shot("01-selection-modal")

        counts = await devtools.eval(
            """(() => {
                const selects = document.querySelectorAll('[role=dialog] select');
                const options = [...selects].map(s => s.options.length);
                const button = [...document.querySelectorAll('[role=dialog] button')]
                    .find(b => b.textContent.includes('শুরু'));
                return { selects: selects.length, options, disabled: button ? button.disabled : null };
            })()"""
        )
        check(
            "popup has three dropdowns (class/subject/chapter)",
            bool(counts) and counts["selects"] == 3,
            json.dumps(counts, ensure_ascii=False),
        )
        check(
            "start button disabled until all three chosen",
            bool(counts) and counts["disabled"] is True,
        )

        # 2. Pick a real chapter through the UI and start the thread.
        await devtools.eval(
            """(() => {
                const [cls, subject, chapter] = document.querySelectorAll('[role=dialog] select');
                const setValue = (el, value) => {
                    el.value = value;
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                };
                setValue(cls, 'class_5');
                setValue(subject, '::bangla');
                return true;
            })()"""
        )
        await devtools.wait_for(
            "document.querySelectorAll('[role=dialog] select')[2].options.length > 5"
        )
        await devtools.eval(
            """(() => {
                const chapter = document.querySelectorAll('[role=dialog] select')[2];
                chapter.value = 'বৈচিত্র্যময় বাংলাদেশ';
                chapter.dispatchEvent(new Event('change', { bubbles: true }));
                return chapter.value;
            })()"""
        )
        await devtools.eval(
            """(() => {
                const button = [...document.querySelectorAll('[role=dialog] button')]
                    .find(b => b.textContent.includes('শুরু'));
                button.click();
                return true;
            })()"""
        )
        closed = await devtools.wait_for("!document.querySelector('[role=dialog]')")
        check("popup closes after submit", closed)
        empty = await devtools.wait_for("document.body.innerText.includes('আজ কী নিয়ে পড়বে')")
        check("empty state with greeting renders", empty)
        await devtools.shot("02-empty-state")

        # 3. Send a question and watch the streamed answer arrive.
        await devtools.eval(
            """(() => {
                const box = document.querySelector('textarea');
                const setter = Object.getOwnPropertyDescriptor(
                    window.HTMLTextAreaElement.prototype, 'value').set;
                setter.call(box, 'বাংলাদেশের উৎসবগুলো কী কী?');
                box.dispatchEvent(new Event('input', { bubbles: true }));
                return true;
            })()"""
        )
        await devtools.eval(
            """(() => {
                const send = [...document.querySelectorAll('button')]
                    .find(b => b.title === 'পাঠাও');
                if (send) send.click();
                return !!send;
            })()"""
        )
        saw_status = await devtools.wait_for(
            "document.body.innerText.includes('খোঁজা হচ্ছে')", timeout=20
        )
        check("loading status shown while retrieving", saw_status)
        answered = await devtools.wait_for(
            "document.body.innerText.includes('উৎস: পাঠ্যবইয়ের')", timeout=120
        )
        check("answer + sources rendered", answered)
        await asyncio.sleep(1.5)
        await devtools.shot("03-chat")

        # 4. Reload with ?thread= to confirm history + context restore.
        await devtools.goto(f"{APP_URL}/?thread={thread_id}" if thread_id else APP_URL)
        restored = await devtools.wait_for(
            "document.body.innerText.includes('উৎস: পাঠ্যবইয়ের')", timeout=60
        )
        check("thread restores from ?thread= deep link", restored)
        context_pill = await devtools.eval(
            """(() => {
                const pill = [...document.querySelectorAll('button')]
                    .find(b => b.textContent.includes('·'));
                return pill ? pill.textContent.trim() : null;
            })()"""
        )
        check(
            "context pill shows class · subject · chapter",
            bool(context_pill) and context_pill.count("·") >= 2,
            str(context_pill),
        )
        await devtools.shot("04-restored")

    failed = [label for label, ok, _ in checks if not ok]
    print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
