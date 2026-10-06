"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { SelectionModal, type PickerResult } from "@/components/selection-modal";
import { Sidebar, type SidebarSection } from "@/components/sidebar";
import { TopBar } from "@/components/top-bar";
import { ChatComposer } from "@/components/chat-composer";
import { EmptyState } from "@/components/empty-state";
import { MessageList } from "@/components/message-list";
import { LoadingScreen, ToastStack, type Toast } from "@/components/toast";
import { ApiError, api, streamChat } from "@/lib/api";
import type {
  ChapterContext,
  ChatMessage,
  Health,
  Source,
  ThreadDetail,
  ThreadGroup,
  TreeResponse,
} from "@/lib/types";
import { useUserName } from "@/lib/use-user-name";

type ModalState = {
  mode: "new" | "switch";
  initial: ChapterContext | null;
};

function toContext(detail: ThreadDetail): ChapterContext | null {
  const context = detail.context;
  if (
    !context.class_id ||
    !context.class_label ||
    !context.subject ||
    !context.subject_label ||
    !context.book ||
    !context.chapter
  ) {
    return null;
  }
  return {
    class_id: context.class_id,
    class_label: context.class_label,
    subject: context.subject,
    subject_label: context.subject_label,
    stream: context.stream ?? null,
    book: context.book,
    chapter: context.chapter,
  };
}

export default function Page() {
  const { userName, saveUserName } = useUserName();

  const [tree, setTree] = useState<TreeResponse | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [groups, setGroups] = useState<ThreadGroup[]>([]);
  const [threadsLoading, setThreadsLoading] = useState(true);

  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [context, setContext] = useState<ChapterContext | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [statusLabel, setStatusLabel] = useState<string | null>(null);
  const [activeSources, setActiveSources] = useState<Source[]>([]);
  const [warning, setWarning] = useState<string | null>(null);

  const [modal, setModal] = useState<ModalState | null>(null);
  const [section, setSection] = useState<SidebarSection>("home");
  const [search, setSearch] = useState("");
  const [navOpen, setNavOpen] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [ready, setReady] = useState(false);
  const [bootError, setBootError] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const toastIdRef = useRef(0);
  const pickerShownRef = useRef(false);

  const pushToast = useCallback((tone: Toast["tone"], message: string) => {
    const id = ++toastIdRef.current;
    setToasts((current) => [...current, { id, tone, message }].slice(-3));
  }, []);

  const dismissToast = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const refreshThreads = useCallback(async () => {
    try {
      setGroups(await api.threads());
    } catch (error) {
      pushToast("error", error instanceof Error ? error.message : "চ্যাট তালিকা লোড হয়নি।");
    } finally {
      setThreadsLoading(false);
    }
  }, [pushToast]);

  const bootstrap = useCallback(async () => {
    setThreadsLoading(true);
    const requestedThread =
      typeof window !== "undefined"
        ? new URLSearchParams(window.location.search).get("thread")
        : null;
    try {
      const [healthResponse, treeResponse] = await Promise.all([api.health(), api.tree()]);
      setHealth(healthResponse);
      setTree(treeResponse);
      setReady(true);
      if (requestedThread) {
        const detail = await api.thread(requestedThread);
        setActiveThreadId(detail.thread_id);
        setMessages(detail.messages);
        setContext(toContext(detail));
        pickerShownRef.current = true;
      }
      void refreshThreads();
    } catch (error) {
      setBootError(
        error instanceof ApiError
          ? error.message
          : "সার্ভারের সাথে সংযোগ করা যায়নি। ব্যাকএন্ড চালু আছে কি?",
      );
    } finally {
      setThreadsLoading(false);
    }
  }, [refreshThreads]);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  // Requirement: the selection popup blocks the app until a class/subject/chapter
  // is chosen, so open it once the app is ready and no thread is loaded yet.
  useEffect(() => {
    if (!ready || pickerShownRef.current || modal || activeThreadId) {
      return;
    }
    pickerShownRef.current = true;
    setModal({ mode: "new", initial: null });
  }, [activeThreadId, modal, ready]);

  const startThread = useCallback(
    async (nextContext: ChapterContext) => {
      const created = await api.createThread(nextContext);
      setActiveThreadId(created.thread_id);
      setMessages(created.messages);
      setContext(toContext(created) ?? nextContext);
      await refreshThreads();
    },
    [refreshThreads],
  );

  const handlePickerSubmit = useCallback(
    async ({ context: picked, startFresh }: PickerResult) => {
      const switchTarget = modal?.mode === "switch" ? activeThreadId : null;
      if (!startFresh && switchTarget) {
        const updated = await api.updateContext(switchTarget, picked);
        setContext(toContext(updated) ?? picked);
        await refreshThreads();
      } else {
        await startThread(picked);
      }
      setModal(null);
      setActiveSources([]);
      setWarning(null);
    },
    [activeThreadId, modal?.mode, refreshThreads, startThread],
  );

  const loadThread = useCallback(
    async (threadId: string) => {
      if (streaming) {
        return;
      }
      setThreadsLoading(true);
      try {
        const detail = await api.thread(threadId);
        setActiveThreadId(detail.thread_id);
        setMessages(detail.messages);
        setContext(toContext(detail));
        setStreamingText("");
        setStatusLabel(null);
        setActiveSources([]);
        setWarning(null);
        setNavOpen(false);
      } catch (error) {
        pushToast("error", error instanceof Error ? error.message : "চ্যাট লোড হয়নি।");
      } finally {
        setThreadsLoading(false);
      }
    },
    [pushToast, streaming],
  );

  const send = useCallback(async () => {
    const question = input.trim();
    if (!question || streaming || !activeThreadId || !context) {
      if (!activeThreadId || !context) {
        pushToast("error", "আগে শ্রেণি, বিষয় ও অধ্যায় বেছে নাও।");
      }
      return;
    }

    setInput("");
    setActiveSources([]);
    setWarning(null);
    setStreamingText("");
    setStatusLabel("পাঠ্যবই খোঁজা হচ্ছে...");
    setStreaming(true);
    setMessages((current) => [
      ...current,
      { role: "user", content: question, sources: [], created_at: new Date().toISOString() },
    ]);

    const controller = new AbortController();
    abortRef.current = controller;
    let answer = "";
    let sources: Source[] = [];
    let failed: string | null = null;

    try {
      for await (const event of streamChat(activeThreadId, question, context, controller.signal)) {
        switch (event.type) {
          case "status":
            setStatusLabel(event.message);
            break;
          case "sources":
            sources = event.sources;
            setActiveSources(event.sources);
            setWarning(event.warning);
            break;
          case "delta":
            answer += event.text;
            setStreamingText(answer);
            break;
          case "error":
            failed = event.message;
            break;
          case "done":
            break;
        }
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        answer = answer || "⏹ থামানো হয়েছে।";
      } else {
        failed = error instanceof Error ? error.message : "উত্তর আনতে সমস্যা হয়েছে।";
      }
    } finally {
      abortRef.current = null;
      setStreaming(false);
      setStatusLabel(null);

      if (failed) {
        if (!answer) {
          answer = failed;
        }
        pushToast("error", failed);
      }
      if (answer) {
        setMessages((current) => [
          ...current,
          {
            role: "assistant",
            content: answer,
            sources: failed && !answer ? [] : sources,
            created_at: new Date().toISOString(),
          },
        ]);
      }
      setStreamingText("");
      setActiveSources([]);
      void refreshThreads();
    }
  }, [activeThreadId, context, input, pushToast, refreshThreads, streaming]);

  const stop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const renameUser = useCallback(() => {
    const next = window.prompt("তোমার নাম কী?", userName);
    if (next !== null) {
      saveUserName(next);
    }
  }, [saveUserName, userName]);

  const openPicker = useCallback(
    (mode: "new" | "switch") => {
      if (streaming) {
        pushToast("info", "উত্তর আসছে — শেষ হলে অধ্যায় বদলাতে পারবে।");
        return;
      }
      setModal({ mode, initial: mode === "switch" ? context : null });
    },
    [context, pushToast, streaming],
  );

  if (bootError && !ready) {
    return (
      <main className="grid min-h-dvh place-items-center p-6">
        <div className="max-w-md rounded-3xl bg-surface p-6 text-center card-shadow">
          <h1 className="text-lg font-bold text-ink">সার্ভারে সংযোগ করা যায়নি</h1>
          <p className="pt-2 text-sm leading-relaxed text-neutral-600">{bootError}</p>
          <p className="pt-2 text-xs text-muted">
            টার্মিনালে চালাও: <code>python -m backend.run</code>
          </p>
          <button
            type="button"
            onClick={() => {
              setBootError(null);
              void bootstrap();
            }}
            className="mt-5 rounded-full bg-ink px-5 py-2.5 text-sm font-medium text-white transition hover:bg-neutral-800"
          >
            আবার চেষ্টা করো
          </button>
        </div>
      </main>
    );
  }

  if (!ready || !tree) {
    return <LoadingScreen label="পাঠ্যবই প্রস্তুত হচ্ছে..." />;
  }

  const contextLabel = context
    ? `${context.class_label} · ${context.subject_label} · ${context.chapter}`
    : null;
  const currentSubject = context
    ? tree.classes
        .flatMap((item) => item.subjects)
        .find((item) => item.book === context.book)
    : undefined;
  const bookHint =
    currentSubject && !currentSubject.indexed
      ? "এই বইটির সূচি (embedding) এখনো তৈরি হয়নি — প্রশ্ন করলে পুরো বই খোঁজার চেষ্টা করা হবে।"
      : null;

  const composer = (
    <ChatComposer
      value={input}
      busy={streaming}
      canStop={streaming}
      hint={contextLabel ?? undefined}
      onChange={setInput}
      onSend={() => void send()}
      onStop={stop}
    />
  );

  return (
    <main className="flex h-dvh gap-4 p-3 sm:p-4">
      <div
        className={`${navOpen ? "flex" : "hidden"} absolute inset-y-0 left-0 z-30 h-full lg:static lg:flex`}
      >
        <div className="h-full overflow-hidden rounded-3xl bg-surface app-shadow lg:rounded-none lg:bg-transparent lg:shadow-none">
          <Sidebar
            userName={userName}
            groups={groups}
            activeThreadId={activeThreadId}
            search={search}
            loading={threadsLoading}
            health={health}
            counts={tree.counts}
            onSearchChange={setSearch}
            onSelectThread={(threadId) => void loadThread(threadId)}
            onSectionChange={setSection}
            onRenameUser={renameUser}
          />
        </div>
      </div>

      {navOpen ? (
        <button
          type="button"
          aria-label="সাইডবার বন্ধ করো"
          onClick={() => setNavOpen(false)}
          className="fixed inset-0 z-20 bg-neutral-900/20 lg:hidden"
        />
      ) : null}

      <section className="flex min-w-0 flex-1 flex-col overflow-hidden rounded-3xl bg-surface app-shadow">
        <TopBar
          userName={userName}
          context={context}
          onOpenPicker={() => openPicker("switch")}
          onNewChat={() => openPicker("new")}
          onToggleNav={() => setNavOpen((open) => !open)}
        />

        <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
          {section === "saved" ? (
            <p className="mx-auto w-full max-w-3xl px-4 py-6 text-xs leading-relaxed text-muted">
              সংরক্ষিত অধ্যায় — এই বৈশিষ্ট্যটি এখনো যোগ করা হয়নি।
            </p>
          ) : null}

          {section === "history" ? (
            <div className="mx-auto w-full max-w-3xl px-4 py-6">
              <h2 className="text-sm font-semibold text-ink">সব চ্যাট</h2>
              <ul className="mt-3 space-y-1.5">
                {groups.flatMap((group) =>
                  group.threads.map((thread) => (
                    <li key={thread.thread_id}>
                      <button
                        type="button"
                        onClick={() => void loadThread(thread.thread_id)}
                        className="w-full rounded-2xl px-3 py-2.5 text-left transition hover:bg-neutral-100"
                      >
                        <span className="block truncate text-[13px] font-medium text-ink">
                          {thread.title}
                        </span>
                        <span className="block truncate pt-0.5 text-[11px] text-muted">
                          {group.label} · {thread.message_count}টি বার্তা
                        </span>
                      </button>
                    </li>
                  )),
                )}
                {groups.length === 0 ? (
                  <li className="text-xs text-muted">এখনো কোনো চ্যাট নেই।</li>
                ) : null}
              </ul>
            </div>
          ) : null}

          {section === "home" ? (
            messages.length === 0 ? (
              <EmptyState userName={userName} contextLabel={contextLabel} hint={bookHint}>
                {composer}
              </EmptyState>
            ) : (
              <MessageList
                messages={messages}
                streamingText={streamingText}
                statusLabel={statusLabel}
                sources={activeSources}
                warning={warning}
              />
            )
          ) : null}
        </div>

        {section === "home" && messages.length > 0 ? (
          <div className="mx-auto w-full max-w-3xl px-4 pb-4">{composer}</div>
        ) : null}
      </section>

      {modal ? (
        <SelectionModal
          classes={tree.classes}
          initialContext={modal.initial}
          mode={modal.mode}
          onCancel={modal.mode === "switch" && activeThreadId ? () => setModal(null) : null}
          onSubmit={handlePickerSubmit}
        />
      ) : null}

      <ToastStack toasts={toasts} onDismiss={dismissToast} />
    </main>
  );
}
