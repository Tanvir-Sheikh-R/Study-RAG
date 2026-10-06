"use client";

import { Bot, ChevronRight, Loader2, User } from "lucide-react";
import { RichText } from "@/components/rich-text";
import type { ChatMessage, Source } from "@/lib/types";

function sourceLabel(source: Source): string {
  const heading = [source.part, source.chapter].filter(Boolean).join(" → ") || "পাঠ্যবই";
  const pages =
    source.page_start != null
      ? source.page_end != null && source.page_end !== source.page_start
        ? `পৃষ্ঠা ${source.page_start}-${source.page_end}`
        : `পৃষ্ঠা ${source.page_start}`
      : null;
  return pages ? `${heading} · ${pages}` : heading;
}

function Sources({ sources }: { sources: Source[] }) {
  if (sources.length === 0) {
    return null;
  }
  return (
    <details className="group mt-3 rounded-2xl bg-neutral-50 px-3 py-2 text-xs text-neutral-600">
      <summary className="flex cursor-pointer items-center gap-1.5 list-none">
        <ChevronRight className="size-3.5 transition group-open:rotate-90" />
        <span>উৎস: পাঠ্যবইয়ের {sources.length}টি অংশ</span>
      </summary>
      <ul className="mt-2 space-y-1.5 pl-5">
        {sources.map((source, index) => (
          <li key={index} className="leading-relaxed">
            <span className="font-medium text-neutral-700">{sourceLabel(source)}</span>
            {source.writer_name ? <span className="text-muted"> · {source.writer_name}</span> : null}
          </li>
        ))}
      </ul>
    </details>
  );
}

export function MessageList({
  messages,
  streamingText,
  statusLabel,
  sources,
  warning,
}: {
  messages: ChatMessage[];
  streamingText: string;
  statusLabel: string | null;
  sources: Source[];
  warning: string | null;
}) {
  return (
    <div className="mx-auto w-full max-w-3xl space-y-6 px-4 py-6">
      {messages.map((message, index) =>
        message.role === "user" ? (
          <div key={index} className="flex justify-end gap-2.5">
            <div className="max-w-[80%] rounded-3xl rounded-br-lg bg-accent px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap text-white">
              {message.content}
            </div>
            <span className="mt-0.5 grid size-7 shrink-0 place-items-center rounded-full bg-neutral-100 text-muted">
              <User className="size-3.5" />
            </span>
          </div>
        ) : (
          <div key={index} className="flex gap-2.5">
            <span className="mt-0.5 grid size-7 shrink-0 place-items-center rounded-full bg-accent-soft text-accent">
              <Bot className="size-3.5" />
            </span>
            <div className="min-w-0 flex-1">
              <RichText text={message.content} />
              <Sources sources={message.sources} />
            </div>
          </div>
        ),
      )}

      {streamingText || statusLabel ? (
        <div className="flex gap-2.5">
          <span className="mt-0.5 grid size-7 shrink-0 place-items-center rounded-full bg-accent-soft text-accent">
            <Bot className="size-3.5" />
          </span>
          <div className="min-w-0 flex-1">
            {streamingText ? (
              <RichText text={streamingText} />
            ) : (
              <p className="flex items-center gap-2 text-sm text-muted">
                <Loader2 className="size-3.5 animate-spin text-accent" />
                {statusLabel}
              </p>
            )}
            {warning ? (
              <p className="mt-2 rounded-2xl bg-amber-50 px-3 py-2 text-xs leading-relaxed text-amber-900 ring-1 ring-amber-200">
                {warning}
              </p>
            ) : null}
            {streamingText ? <Sources sources={sources} /> : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}
