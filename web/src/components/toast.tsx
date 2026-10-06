"use client";

import { Loader2, TriangleAlert, X } from "lucide-react";

export type Toast = {
  id: number;
  tone: "error" | "info";
  message: string;
};

export function ToastStack({
  toasts,
  onDismiss,
}: {
  toasts: Toast[];
  onDismiss: (id: number) => void;
}) {
  if (toasts.length === 0) {
    return null;
  }
  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-6 z-50 flex flex-col items-center gap-2 px-4">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          role="alert"
          className={`bb-slide-up pointer-events-auto flex max-w-xl items-start gap-3 rounded-2xl px-4 py-3 text-sm app-shadow ${
            toast.tone === "error"
              ? "bg-rose-50 text-rose-900 ring-1 ring-rose-200"
              : "bg-white text-neutral-700 ring-1 ring-neutral-200"
          }`}
        >
          <TriangleAlert className="mt-0.5 size-4 shrink-0" />
          <p className="flex-1 leading-relaxed">{toast.message}</p>
          <button
            type="button"
            onClick={() => onDismiss(toast.id)}
            aria-label="বার্তা বন্ধ করুন"
            className="rounded-full p-1 transition hover:bg-black/5"
          >
            <X className="size-3.5" />
          </button>
        </div>
      ))}
    </div>
  );
}

export function LoadingScreen({ label }: { label: string }) {
  return (
    <div className="flex min-h-dvh items-center justify-center p-4">
      <div className="flex items-center gap-3 rounded-2xl bg-surface px-6 py-4 text-sm text-neutral-600 app-shadow">
        <Loader2 className="size-4 animate-spin text-accent" />
        <span>{label}</span>
      </div>
    </div>
  );
}
