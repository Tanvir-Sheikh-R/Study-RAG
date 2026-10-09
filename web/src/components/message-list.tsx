"use client";

import { Bot, Loader2, User } from "lucide-react";
import { RichText } from "@/components/rich-text";
import type { ChatMessage } from "@/lib/types";

export function MessageList({
  messages,
  streamingText,
  statusLabel,
}: {
  messages: ChatMessage[];
  streamingText: string;
  statusLabel: string | null;
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
          </div>
        </div>
      ) : null}
    </div>
  );
}
