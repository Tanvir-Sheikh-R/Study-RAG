// Verifies the frontend's NDJSON stream handling against the live API.
// The app parses chunk-boundary-split newline-delimited JSON in web/src/lib/api.ts;
// this test replays that same algorithm over the real byte stream.
//
//   node scripts/verify-stream.mjs <thread_id>

const API = "http://127.0.0.1:8000";
const threadId = process.argv[2];
if (!threadId) {
  console.error("usage: node scripts/verify-stream.mjs <thread_id>");
  process.exit(2);
}

const CONTEXT = {
  class_id: "class_5",
  class_label: "৫ম শ্রেণি",
  subject: "bangla",
  subject_label: "বাংলা",
  stream: null,
  book: "class_5/bangla",
  chapter: "বৈচিত্র্যময় বাংলাদেশ",
};

const checks = [];
const check = (label, ok, detail = "") => {
  checks.push([label, ok]);
  console.log(`${ok ? "PASS" : "FAIL"}  ${label}${detail ? ` — ${detail}` : ""}`);
};

const response = await fetch(`${API}/api/threads/${threadId}/chat`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ message: "বাংলাদেশের উৎসবগুলো কী কী?", context: CONTEXT }),
});

check("chat endpoint returns 200", response.ok, `HTTP ${response.status}`);
check("content-type is NDJSON", (response.headers.get("content-type") ?? "").includes("ndjson"));

const reader = response.body.getReader();
const decoder = new TextDecoder();
let buffer = "";
const events = [];
let chunkCount = 0;

// Same incremental parse as web/src/lib/api.ts.
for (;;) {
  const { done, value } = await reader.read();
  if (done) break;
  chunkCount += 1;
  buffer += decoder.decode(value, { stream: true });
  let newline = buffer.indexOf("\n");
  while (newline !== -1) {
    const line = buffer.slice(0, newline).trim();
    buffer = buffer.slice(newline + 1);
    if (line) events.push(JSON.parse(line));
    newline = buffer.indexOf("\n");
  }
}
if (buffer.trim()) events.push(JSON.parse(buffer.trim()));

const kinds = [...new Set(events.map((event) => event.type))];
const statuses = events.filter((event) => event.type === "status").map((event) => event.stage);
const sources = events.find((event) => event.type === "sources");
const deltas = events.filter((event) => event.type === "delta");
const done = events.find((event) => event.type === "done");
const errors = events.filter((event) => event.type === "error");
const answer = deltas.map((event) => event.text).join("");

console.log(
  `\n${events.length} events in ${chunkCount} network chunks; kinds=${kinds.join(", ")}; deltas=${deltas.length}`,
);

check("stream carried real network chunks", chunkCount >= 1, `${chunkCount} chunks`);
check("no error events", errors.length === 0, errors.map((e) => e.message).join(" | "));
check("every event is a known type", kinds.every((k) => ["status", "sources", "delta", "done"].includes(k)), kinds.join(", "));
check("status events report searching then answering", statuses.join(",") === "searching,answering", statuses.join(","));
check("sources arrive before the first delta", events.findIndex((e) => e.type === "sources") < events.findIndex((e) => e.type === "delta"));
check("sources carry chapter + page metadata", Boolean(sources?.sources?.length) && sources.sources.every((s) => s.chapter && s.snippet), `${sources?.sources?.length ?? 0} sources`);
check("answer streamed as many deltas", deltas.length > 5, `${deltas.length} deltas`);
check("assembled answer is Bengali text", /[\u0980-\u09FF]/.test(answer) && answer.length > 100, `${answer.length} chars`);
check("done event closes the stream last", events[events.length - 1]?.type === "done", events[events.length - 1]?.type);
check("done reports the thread id", done?.thread_id === threadId);

const failed = checks.filter(([, ok]) => !ok);
console.log(`\n${checks.length - failed.length}/${checks.length} checks passed`);
process.exit(failed.length === 0 ? 0 : 1);
