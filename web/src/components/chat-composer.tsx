"use client";

import {
  ArrowUp,
  ListChecks,
  Loader2,
  Paperclip,
  ScrollText,
  Sparkle,
  Square,
  Sparkles,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

const QUICK_ACTIONS: { label: string; prompt: string; icon: LucideIcon }[] = [
  {
    label: "সারাংশ দাও",
    prompt: "এই অধ্যায়ের মূল বিষয়গুলো সংক্ষেপে সারাংশ আকারে বলে দাও।",
    icon: ScrollText,
  },
  {
    label: "কুইজ বানাও",
    prompt: "এই অধ্যায় থেকে ৫টি সংক্ষিপ্ত প্রশ্ন বানাও এবং শেষে উত্তরগুলো দাও।",
    icon: ListChecks,
  },
  {
    label: "বিস্তারিত ব্যাখ্যা",
    prompt: "এই অধ্যায়ের সবচেয়ে গুরুত্বপূর্ণ বিষয়টি সহজ ভাষায় বিস্তারিত বুঝিয়ে দাও।",
    icon: Sparkle,
  },
];

export function ChatComposer({
  value,
  busy,
  canStop,
  hint,
  onChange,
  onSend,
  onStop,
}: {
  value: string;
  busy: boolean;
  canStop: boolean;
  hint?: string;
  onChange: (value: string) => void;
  onSend: () => void;
  onStop: () => void;
}) {
  const disabled = value.trim().length === 0 || busy;

  return (
    <div className="rounded-3xl bg-surface p-4 card-shadow">
      <div className="flex items-start gap-2.5">
        <Sparkles className="mt-0.5 size-4 shrink-0 text-accent" />
        <textarea
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              if (!disabled) {
                onSend();
              }
            }
          }}
          rows={2}
          placeholder="প্রশ্ন লিখুন বা কমান্ড দিন..."
          aria-label="প্রশ্ন লিখুন"
          className="max-h-40 min-h-[52px] flex-1 resize-none bg-transparent text-sm leading-relaxed text-ink outline-none placeholder:text-muted"
        />
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        <button
          type="button"
          disabled
          title="ফাইল সংযুক্তি এখনো যোগ করা হয়নি"
          className="grid size-7 shrink-0 place-items-center rounded-full text-muted/60"
        >
          <Paperclip className="size-3.5" />
        </button>

        {QUICK_ACTIONS.map((action) => {
          const Icon = action.icon;
          return (
            <button
              key={action.label}
              type="button"
              onClick={() => onChange(action.prompt)}
              className="flex items-center gap-1.5 rounded-full border border-neutral-200 bg-white px-2.5 py-1.5 text-[11.5px] text-neutral-600 transition hover:border-accent/40 hover:text-accent-strong"
            >
              <Icon className="size-3" />
              {action.label}
            </button>
          );
        })}

        <div className="flex flex-1 items-center justify-end gap-2">
          {hint ? <span className="truncate text-[11px] text-muted">{hint}</span> : null}
          {canStop ? (
            <button
              type="button"
              onClick={onStop}
              title="থামাও"
              className="grid size-9 place-items-center rounded-full bg-accent text-white transition hover:bg-accent-strong"
            >
              <Square className="size-3.5" />
            </button>
          ) : (
            <button
              type="button"
              onClick={onSend}
              disabled={disabled}
              title="পাঠাও"
              className="grid size-9 place-items-center rounded-full bg-accent text-white transition hover:bg-accent-strong disabled:cursor-not-allowed disabled:bg-neutral-200 disabled:text-muted"
            >
              {busy ? <Loader2 className="size-4 animate-spin" /> : <ArrowUp className="size-4" />}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
