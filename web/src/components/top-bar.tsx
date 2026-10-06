"use client";

import { BookOpen, ChevronsUpDown, PanelLeft, Plus } from "lucide-react";
import { Avatar } from "@/components/avatar";
import type { ChapterContext } from "@/lib/types";

export function TopBar({
  userName,
  context,
  onOpenPicker,
  onNewChat,
  onToggleNav,
}: {
  userName: string;
  context: ChapterContext | null;
  onOpenPicker: () => void;
  onNewChat: () => void;
  onToggleNav: () => void;
}) {
  const text = context
    ? `${context.class_label} · ${context.subject_label} · ${context.chapter}`
    : "শ্রেণি · বিষয় · অধ্যায় নির্বাচন করো";

  return (
    <header className="flex items-center justify-between gap-3 border-b border-neutral-200/70 px-4 py-3">
      <div className="flex min-w-0 items-center gap-2">
        <button
          type="button"
          onClick={onToggleNav}
          aria-label="সাইডবার"
          className="rounded-xl p-2 text-muted transition hover:bg-neutral-100 hover:text-ink lg:hidden"
        >
          <PanelLeft className="size-4" />
        </button>

        <button
          type="button"
          onClick={onOpenPicker}
          title="শ্রেণি, বিষয় ও অধ্যায় বদলাও"
          className="flex min-w-0 items-center gap-2 rounded-full bg-neutral-100 py-2 pr-3 pl-2.5 transition hover:bg-neutral-200/70"
        >
          <span className="grid size-6 shrink-0 place-items-center rounded-full bg-white text-accent">
            <BookOpen className="size-3.5" />
          </span>
          <span className="truncate text-[13px] font-medium text-ink">{text}</span>
          <ChevronsUpDown className="size-3.5 shrink-0 text-muted" />
        </button>
      </div>

      <div className="flex shrink-0 items-center gap-2.5">
        <button
          type="button"
          onClick={onNewChat}
          className="flex items-center gap-1.5 rounded-full bg-ink px-4 py-2 text-[13px] font-medium text-white transition hover:bg-neutral-800"
        >
          <Plus className="size-3.5" />
          <span className="hidden sm:inline">নতুন চ্যাট</span>
        </button>
        <Avatar name={userName} />
      </div>
    </header>
  );
}
