"use client";

import {
  Bookmark,
  History,
  Home,
  Loader2,
  Menu,
  MessageSquare,
  Search,
  Settings2,
} from "lucide-react";
import { Avatar } from "@/components/avatar";
import type { Health, ThreadGroup, TreeCounts } from "@/lib/types";

export type SidebarSection = "home" | "saved" | "history";

const NAV_ITEMS: { id: SidebarSection; label: string; icon: typeof Home }[] = [
  { id: "home", label: "হোম", icon: Home },
  { id: "saved", label: "সংরক্ষিত", icon: Bookmark },
  { id: "history", label: "ইতিহাস", icon: History },
];

export function Sidebar({
  userName,
  groups,
  activeThreadId,
  search,
  loading,
  health,
  counts,
  onSearchChange,
  onSelectThread,
  onSectionChange,
  onRenameUser,
}: {
  userName: string;
  groups: ThreadGroup[];
  activeThreadId: string | null;
  search: string;
  loading: boolean;
  health: Health | null;
  counts: TreeCounts | null;
  onSearchChange: (value: string) => void;
  onSelectThread: (threadId: string) => void;
  onSectionChange: (section: SidebarSection) => void;
  onRenameUser: () => void;
}) {
  const query = search.trim().toLowerCase();
  const visibleGroups = groups
    .map((group) => ({
      label: group.label,
      threads: query
        ? group.threads.filter(
            (thread) =>
              thread.title.toLowerCase().includes(query) ||
              thread.preview.toLowerCase().includes(query),
          )
        : group.threads,
    }))
    .filter((group) => group.threads.length > 0);

  const totalThreads = groups.reduce((sum, group) => sum + group.threads.length, 0);

  return (
    <aside className="flex w-[260px] shrink-0 flex-col border-r border-neutral-200/70 bg-surface">
      <div className="flex items-center gap-2.5 px-5 pt-5 pb-4">
        <span className="grid size-8 place-items-center rounded-xl bg-accent text-white">
          <Bookmark className="size-4" />
        </span>
        <span className="text-base font-bold tracking-tight text-ink">বই বন্ধু</span>
      </div>

      <div className="px-4">
        <div className="flex items-center gap-2 rounded-full bg-neutral-100 px-3 py-2 transition focus-within:bg-neutral-50 focus-within:ring-2 focus-within:ring-accent/25">
          <Search className="size-3.5 shrink-0 text-muted" />
          <input
            value={search}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="খুঁজুন"
            aria-label="চ্যাট খুঁজুন"
            className="min-w-0 flex-1 bg-transparent text-xs text-ink outline-none placeholder:text-muted"
          />
          <kbd className="rounded-md border border-neutral-200 bg-white px-1.5 py-0.5 text-[10px] font-medium text-muted">
            ⌘K
          </kbd>
        </div>
      </div>

      <nav className="mt-3 space-y-0.5 px-3">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onSectionChange(item.id)}
              className="flex w-full items-center gap-2.5 rounded-xl px-2.5 py-2 text-left text-[13px] text-neutral-600 transition hover:bg-neutral-100 hover:text-ink"
            >
              <Icon className="size-4 shrink-0 text-muted" />
              <span className="flex-1">{item.label}</span>
              {item.id === "history" && totalThreads > 0 ? (
                <span className="text-[11px] text-muted">{totalThreads}</span>
              ) : null}
            </button>
          );
        })}
      </nav>

      <div className="mt-4 flex min-h-0 flex-1 flex-col">
        <div className="flex items-center justify-between px-5 pb-2">
          <span className="text-[11px] font-medium tracking-wide text-muted">চ্যাট</span>
          <button
            type="button"
            onClick={() => onSectionChange("history")}
            aria-label="সব চ্যাট"
            className="rounded-md p-1 text-muted transition hover:bg-neutral-100 hover:text-ink"
          >
            <Menu className="size-3.5" />
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-3 pb-4">
          {loading ? (
            <p className="flex items-center gap-2 px-2 py-3 text-xs text-muted">
              <Loader2 className="size-3.5 animate-spin" /> চ্যাট লোড হচ্ছে...
            </p>
          ) : visibleGroups.length === 0 ? (
            <p className="px-2 py-3 text-xs leading-relaxed text-muted">
              {query ? "কিছু পাওয়া যায়নি।" : "এখনো কোনো চ্যাট নেই — “নতুন চ্যাট” চাপো।"}
            </p>
          ) : (
            visibleGroups.map((group) => (
              <div key={group.label} className="mb-3">
                <p className="px-2 pb-1.5 text-[11px] text-muted">{group.label}</p>
                <div className="space-y-0.5">
                  {group.threads.map((thread) => {
                    const active = thread.thread_id === activeThreadId;
                    return (
                      <button
                        key={thread.thread_id}
                        type="button"
                        onClick={() => onSelectThread(thread.thread_id)}
                        title={thread.title}
                        className={`flex w-full items-center gap-2 rounded-xl px-2.5 py-2 text-left text-[12.5px] transition ${
                          active
                            ? "bg-accent-soft text-accent-strong"
                            : "text-neutral-600 hover:bg-neutral-100 hover:text-ink"
                        }`}
                      >
                        <MessageSquare
                          className={`size-3.5 shrink-0 ${active ? "text-accent" : "text-muted"}`}
                        />
                        <span className="truncate">{thread.title}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="border-t border-neutral-200/70 px-3 py-3">
        <button
          type="button"
          onClick={onRenameUser}
          className="flex w-full items-center gap-2.5 rounded-xl px-2 py-2 text-left transition hover:bg-neutral-100"
        >
          <Avatar name={userName} />
          <span className="min-w-0 flex-1">
            <span className="block truncate text-[13px] font-medium text-ink">{userName}</span>
            <span className="block truncate text-[11px] text-muted">
              {counts
                ? `${counts.indexed_books} বই প্রস্তুত · ${counts.chapters} চ্যাপটার`
                : "পাঠ্যবই অ্যাসিস্ট্যান্ট"}
            </span>
          </span>
          <Settings2 className="size-3.5 shrink-0 text-muted" />
        </button>
        {health ? (
          <p className="px-2 pt-1 text-[10px] leading-relaxed text-muted">
            {health.llm_model} · {health.device} · {health.dimension}d
          </p>
        ) : null}
      </div>
    </aside>
  );
}
