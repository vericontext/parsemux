"use client";

import ReactMarkdown from "react-markdown";
import rehypeRaw from "rehype-raw";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";
import remarkGfm from "remark-gfm";
import type { ParseResult } from "@/lib/api";

// Allow standard HTML tags (like <br>) but strip unknown ones (like <pad>)
const sanitizeSchema = {
  ...defaultSchema,
  tagNames: [
    ...(defaultSchema.tagNames ?? []),
    "br",
    "sup",
    "sub",
    "mark",
    "del",
    "ins",
  ],
};

export function ResultView({
  content,
  format,
  result,
}: {
  content: string;
  format: "markdown" | "text" | "json";
  result?: ParseResult;
}) {
  if (format === "json") {
    const data = result ?? content;
    return (
      <pre className="font-mono text-sm whitespace-pre-wrap break-words">
        {JSON.stringify(data, null, 2)}
      </pre>
    );
  }

  if (format === "text") {
    return <pre className="font-mono text-sm whitespace-pre-wrap leading-relaxed">{content}</pre>;
  }

  return (
    <div className="prose-parsemux">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw, [rehypeSanitize, sanitizeSchema]]}
        urlTransform={(url) => url}
        components={{
          img: ({ src, alt, ...props }) => (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={src}
              alt={alt || ""}
              className="rounded-lg max-w-full border border-border my-3"
              loading="lazy"
              {...props}
            />
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
