"use client";

import { GradientOrb } from "@/components/gradient-orb";

export function EmptyState({
  userName,
  contextLabel,
  hint,
  children,
}: {
  userName: string;
  contextLabel: string | null;
  hint: string | null;
  children: React.ReactNode;
}) {
  const hour = new Date().getHours();
  const greeting =
    hour < 6
      ? "শুভ রাত্রি"
      : hour < 12
        ? "শুভ সকাল"
        : hour < 16
          ? "শুভ দুপুর"
          : hour < 19
            ? "শুভ বিকেল"
            : "শুভ সন্ধ্যা";

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col items-center justify-center px-4 py-10">
      <GradientOrb />

      <h1 className="pt-6 text-center text-2xl leading-snug font-bold text-ink sm:text-[28px]">
        {greeting}, {userName}
      </h1>
      <p className="pt-1 text-center text-2xl leading-snug font-bold sm:text-[28px]">
        <span className="text-accent">আজ কী নিয়ে পড়বে?</span>
      </p>

      {contextLabel ? (
        <p className="pt-3 text-center text-xs text-muted">{contextLabel}</p>
      ) : null}
      {hint ? (
        <p className="max-w-md pt-2 text-center text-xs leading-relaxed text-amber-700">{hint}</p>
      ) : null}

      <div className="w-full pt-6">{children}</div>
    </div>
  );
}
