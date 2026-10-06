export function Avatar({ name, className = "" }: { name: string; className?: string }) {
  const initial = name.trim().charAt(0) || "ব";
  return (
    <span
      aria-hidden
      className={`grid size-8 shrink-0 place-items-center rounded-full bg-accent-soft text-sm font-semibold text-accent ${className}`}
    >
      {initial}
    </span>
  );
}
