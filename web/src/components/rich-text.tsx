import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/** Renders the assistant's Markdown (headings, rules, lists, tables, bold, code). */
export function RichText({ text }: { text: string }) {
  return (
    <div className="text-sm leading-[1.85] text-neutral-800">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <h1 className="pt-2 text-lg font-bold text-ink first:pt-0">{children}</h1>
          ),
          h2: ({ children }) => (
            <h2 className="pt-2 text-base font-bold text-ink first:pt-0">{children}</h2>
          ),
          h3: ({ children }) => (
            <h3 className="pt-1.5 text-[15px] font-semibold text-ink first:pt-0">{children}</h3>
          ),
          h4: ({ children }) => (
            <h4 className="pt-1 text-sm font-semibold text-ink first:pt-0">{children}</h4>
          ),
          p: ({ children }) => <p className="whitespace-pre-wrap py-0.5">{children}</p>,
          ul: ({ children }) => (
            <ul className="my-1 list-disc space-y-0.5 pl-5">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="my-1 list-decimal space-y-0.5 pl-5">{children}</ol>
          ),
          li: ({ children }) => <li className="leading-relaxed">{children}</li>,
          hr: () => <hr className="my-3 border-neutral-200" />,
          strong: ({ children }) => <strong className="font-semibold text-ink">{children}</strong>,
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noreferrer"
              className="text-accent underline decoration-accent/40 underline-offset-2"
            >
              {children}
            </a>
          ),
          code: ({ children }) => (
            <code className="rounded bg-neutral-100 px-1 py-0.5 text-[0.9em]">{children}</code>
          ),
          pre: ({ children }) => (
            <pre className="my-2 overflow-x-auto rounded-2xl bg-neutral-100 p-3 text-[13px] leading-relaxed">
              {children}
            </pre>
          ),
          blockquote: ({ children }) => (
            <blockquote className="my-2 border-l-2 border-accent/40 pl-3 text-neutral-600">
              {children}
            </blockquote>
          ),
          table: ({ children }) => (
            <div className="my-2 overflow-x-auto">
              <table className="w-full border-collapse text-[13px]">{children}</table>
            </div>
          ),
          th: ({ children }) => (
            <th className="border border-neutral-200 bg-neutral-50 px-2.5 py-1.5 text-left font-semibold text-ink">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border border-neutral-200 px-2.5 py-1.5 align-top">{children}</td>
          ),
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}
