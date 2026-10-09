"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, TriangleAlert, X } from "lucide-react";
import type { ClassNode, ChapterContext, Subject } from "@/lib/types";

export type PickerResult = {
  context: ChapterContext;
  startFresh: boolean;
};

const CHAPTER_SEARCH_THRESHOLD = 40;

export function SelectionModal({
  classes,
  initialContext,
  mode,
  onCancel,
  onSubmit,
}: {
  classes: ClassNode[];
  initialContext: ChapterContext | null;
  /** "new" starts a fresh thread; "switch" re-targets the current conversation. */
  mode: "new" | "switch";
  onCancel: (() => void) | null;
  onSubmit: (result: PickerResult) => Promise<void>;
}) {
  const [classId, setClassId] = useState<string>(
    initialContext?.class_id ?? classes[0]?.class_id ?? "",
  );
  const [subjectKey, setSubjectKey] = useState<string>(
    initialContext ? `${initialContext.stream ?? ""}::${initialContext.subject}` : "",
  );
  const [chapterName, setChapterName] = useState<string>(initialContext?.chapter ?? "");
  const [chapterQuery, setChapterQuery] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const classNode = classes.find((item) => item.class_id === classId) ?? null;
  const subjects = classNode?.subjects ?? [];
  const subject: Subject | null =
    subjects.find((item) => `${item.stream ?? ""}::${item.subject}` === subjectKey) ?? null;
  const chapters = subject?.chapters ?? [];

  const query = chapterQuery.trim().toLowerCase();
  const visibleChapters = query
    ? chapters.filter((chapter) => chapter.name.toLowerCase().includes(query))
    : chapters;

  const initialClassId = initialContext?.class_id ?? null;

  // Reset the dependent dropdowns only when the parent choice actually changed,
  // so reopening the modal keeps the chapter the conversation is already on.
  useEffect(() => {
    if (classId === initialClassId) {
      return;
    }
    setSubjectKey("");
    setChapterName("");
    setChapterQuery("");
  }, [classId, initialClassId]);

  // Clear the chapter when a different subject is picked (not on first render).
  const previousSubjectKey = useRef(subjectKey);
  useEffect(() => {
    if (previousSubjectKey.current === subjectKey) {
      return;
    }
    previousSubjectKey.current = subjectKey;
    setChapterName("");
    setChapterQuery("");
  }, [subjectKey]);

  const ready = Boolean(classNode && subject && chapterName);

  async function handleSubmit() {
    if (!classNode || !subject || !chapterName || submitting) {
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await onSubmit({
        startFresh: mode === "new",
        context: {
          class_id: classNode.class_id,
          class_label: classNode.label,
          subject: subject.subject,
          subject_label: subject.label,
          stream: subject.stream,
          book: subject.book,
          chapter: chapterName,
        },
      });
    } catch (submitError) {
      setError(
        submitError instanceof Error ? submitError.message : "শুরু করা যায়নি, আবার চেষ্টা করো।",
      );
      setSubmitting(false);
    }
  }

  return (
    <div className="bb-fade-in fixed inset-0 z-40 grid place-items-center bg-neutral-900/25 p-4 backdrop-blur-sm">
      <div
        role="dialog"
        aria-modal="true"
        aria-label="পাঠ্যবই নির্বাচন"
        className="bb-slide-up max-h-[92dvh] w-full max-w-lg overflow-y-auto rounded-3xl bg-surface p-6 card-shadow"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-ink">
              {mode === "new" ? "কী পড়তে চাও?" : "অধ্যায় বদলাও"}
            </h2>
            <p className="pt-1 text-xs leading-relaxed text-muted">
              শ্রেণি, বিষয় ও অধ্যায় বেছে নাও — উত্তর আসবে ঠিক সেই অধ্যায় থেকে।
            </p>
          </div>
          {onCancel ? (
            <button
              type="button"
              onClick={onCancel}
              aria-label="বন্ধ করো"
              className="rounded-full p-1.5 text-muted transition hover:bg-neutral-100 hover:text-ink"
            >
              <X className="size-4" />
            </button>
          ) : null}
        </div>

        <div className="space-y-4 pt-5">
          <Field label="ক্লাস">
            <select
              value={classId}
              onChange={(event) => setClassId(event.target.value)}
              className="w-full appearance-none rounded-2xl border border-neutral-200 bg-white px-4 py-2.5 text-sm text-ink outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/20"
            >
              {classes.map((item) => (
                <option key={item.class_id} value={item.class_id}>
                  {item.label}
                </option>
              ))}
            </select>
          </Field>

          <Field label="বিষয়">
            <select
              value={subjectKey}
              onChange={(event) => setSubjectKey(event.target.value)}
              disabled={!classNode}
              className="w-full appearance-none rounded-2xl border border-neutral-200 bg-white px-4 py-2.5 text-sm text-ink outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/20 disabled:bg-neutral-50 disabled:text-muted"
            >
              <option value="">বিষয় বেছে নাও</option>
              {subjects.map((item) => {
                const key = `${item.stream ?? ""}::${item.subject}`;
                const streamLabel = item.stream && classNode?.nested ? `${item.stream} · ` : "";
                return (
                  <option key={key} value={key}>
                    {streamLabel}
                    {item.label}
                    {item.indexed ? "" : " (সূচি নেই)"}
                  </option>
                );
              })}
            </select>
            {classNode?.nested ? (
              <p className="pt-1.5 text-[11px] leading-relaxed text-muted">
                ৯ম-১০ম শ্রেণিতে বিষয়ের আগে বিভাগ আছে: general, science, arts, commerce।
              </p>
            ) : null}
          </Field>

          <Field label="চ্যাপটার" hint={chapters.length > 0 ? `${chapters.length}টি` : undefined}>
            {chapters.length > CHAPTER_SEARCH_THRESHOLD ? (
              <input
                value={chapterQuery}
                onChange={(event) => setChapterQuery(event.target.value)}
                placeholder="অধ্যায় খুঁজুন..."
                className="mb-2 w-full rounded-2xl border border-neutral-200 bg-white px-4 py-2 text-xs text-ink outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/20"
              />
            ) : null}
            <select
              value={chapterName}
              onChange={(event) => setChapterName(event.target.value)}
              disabled={chapters.length === 0}
              className="w-full appearance-none rounded-2xl border border-neutral-200 bg-white px-4 py-2.5 text-sm text-ink outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/20 disabled:bg-neutral-50 disabled:text-muted"
            >
              <option value="">
                {chapters.length === 0 ? "আগে বিষয় বেছে নাও" : "অধ্যায় বেছে নাও"}
              </option>
              {visibleChapters.map((chapter) => (
                <option key={`${chapter.number}-${chapter.name}`} value={chapter.name}>
                  {chapter.parent ? `${chapter.parent} — ${chapter.name}` : chapter.name}
                  {chapter.writer_name ? ` · ${chapter.writer_name}` : ""}
                  {chapter.starting_page ? ` — পৃষ্ঠা ${chapter.starting_page}` : ""}
                </option>
              ))}
            </select>
          </Field>

          {error ? (
            <p className="flex items-start gap-2 rounded-2xl bg-rose-50 px-4 py-3 text-xs leading-relaxed text-rose-800 ring-1 ring-rose-200">
              <TriangleAlert className="mt-0.5 size-3.5 shrink-0" />
              {error}
            </p>
          ) : null}
        </div>

        <button
          type="button"
          onClick={handleSubmit}
          disabled={!ready || submitting}
          className="mt-6 flex w-full items-center justify-center gap-2 rounded-full bg-ink py-3 text-sm font-semibold text-white transition hover:bg-neutral-800 disabled:cursor-not-allowed disabled:bg-neutral-300"
        >
          {submitting ? (
            <>
              <Loader2 className="size-4 animate-spin" /> শুরু হচ্ছে...
            </>
          ) : (
            "শুরু করুন"
          )}
        </button>
      </div>
    </div>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="flex items-baseline justify-between pb-1.5">
        <span className="text-xs font-medium text-neutral-700">{label}</span>
        {hint ? <span className="text-[11px] text-muted">{hint}</span> : null}
      </div>
      {children}
    </div>
  );
}
