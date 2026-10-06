import type {
  ChapterContext,
  Health,
  StreamEvent,
  ThreadDetail,
  ThreadGroup,
  TreeResponse,
} from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function readError(response: Response): Promise<string> {
  const text = await response.text();
  if (!text) {
    return `অনুরোধ ব্যর্থ হয়েছে (HTTP ${response.status})`;
  }
  try {
    const parsed = JSON.parse(text) as { detail?: unknown };
    const detail = parsed.detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (Array.isArray(detail)) {
      return detail
        .map((item) => {
          if (item && typeof item === "object" && "msg" in item) {
            return String((item as { msg: unknown }).msg);
          }
          return JSON.stringify(item);
        })
        .join("; ");
    }
  } catch {
    return text.slice(0, 300);
  }
  return text.slice(0, 300);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
      cache: "no-store",
    });
  } catch (error) {
    throw new ApiError(
      `সার্ভারে সংযোগ করা যায়নি (${API_BASE})। ব্যাকএন্ড চালু আছে কি? ${
        error instanceof Error ? error.message : ""
      }`.trim(),
      0,
    );
  }
  if (!response.ok) {
    throw new ApiError(await readError(response), response.status);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export const api = {
  health: () => request<Health>("/api/health"),
  tree: () => request<TreeResponse>("/api/tree"),
  threads: () => request<ThreadGroup[]>("/api/threads"),
  thread: (threadId: string) => request<ThreadDetail>(`/api/threads/${threadId}`),
  createThread: (context: ChapterContext) =>
    request<ThreadDetail>("/api/threads", {
      method: "POST",
      body: JSON.stringify({ context }),
    }),
  updateContext: (threadId: string, context: ChapterContext) =>
    request<ThreadDetail>(`/api/threads/${threadId}/context`, {
      method: "PUT",
      body: JSON.stringify({ context }),
    }),
  deleteThread: (threadId: string) =>
    request<void>(`/api/threads/${threadId}`, { method: "DELETE" }),
};

/**
 * POSTs a question and yields parsed NDJSON events as they arrive.
 * NDJSON (one JSON object per line) is used instead of SSE because the request
 * carries a body and must surface errors mid-stream.
 */
export async function* streamChat(
  threadId: string,
  message: string,
  context: ChapterContext,
  signal?: AbortSignal,
): AsyncGenerator<StreamEvent> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/threads/${threadId}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, context }),
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      return;
    }
    throw new ApiError(
      `উত্তর আনার অনুরোধ পাঠানো যায়নি: ${error instanceof Error ? error.message : ""}`.trim(),
      0,
    );
  }

  if (!response.ok) {
    throw new ApiError(await readError(response), response.status);
  }
  if (!response.body) {
    throw new ApiError("সার্ভার থেকে কোনো স্ট্রিম পাওয়া যায়নি।", response.status);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      let newline = buffer.indexOf("\n");
      while (newline !== -1) {
        const line = buffer.slice(0, newline).trim();
        buffer = buffer.slice(newline + 1);
        if (line) {
          yield JSON.parse(line) as StreamEvent;
        }
        newline = buffer.indexOf("\n");
      }
    }
    const tail = buffer.trim();
    if (tail) {
      yield JSON.parse(tail) as StreamEvent;
    }
  } finally {
    reader.releaseLock();
  }
}
