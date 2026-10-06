import type { ReactNode } from "react";

/** Very small formatter: **bold** and `code`, everything else stays literal text. */
export function InlineText({ text }: { text: string }): ReactNode {
  const nodes: ReactNode[] = [];
  let cursor = 0;
  let key = 0;

  // Built per call: a shared global regex would keep lastIndex between renders.
  const pattern = /\*\*([^*]+)\*\*|`([^`]+)`/g;
  for (const match of text.matchAll(pattern)) {
    const index = match.index ?? 0;
    if (index > cursor) {
      nodes.push(text.slice(cursor, index));
    }
    if (match[1] !== undefined) {
      nodes.push(
        <strong key={key++} className="font-semibold text-ink">
          {match[1]}
        </strong>,
      );
    } else if (match[2] !== undefined) {
      nodes.push(
        <code key={key++} className="rounded bg-neutral-100 px-1 py-0.5 text-[0.9em]">
          {match[2]}
        </code>,
      );
    }
    cursor = index + match[0].length;
  }
  if (cursor < text.length) {
    nodes.push(text.slice(cursor));
  }
  return <>{nodes}</>;
}

export function RichText({ text }: { text: string }) {
  return (
    <div className="space-y-2 text-sm leading-[1.85] text-neutral-800">
      {text.split("\n").map((line, index) => {
        if (!line.trim()) {
          return <span key={index} className="block h-1.5" />;
        }
        return (
          <p key={index} className="whitespace-pre-wrap">
            <InlineText text={line} />
          </p>
        );
      })}
    </div>
  );
}
