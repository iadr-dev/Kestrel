"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Props {
  content: string;
}

export function MarkdownContent({ content }: Props) {
  return (
    <div className="markdown-content prose prose-sm dark:prose-invert max-w-none prose-p:my-2 prose-headings:mt-4 prose-headings:mb-2 prose-li:my-0.5 prose-code:text-signal prose-code:bg-raised prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none prose-pre:bg-surface prose-pre:border prose-pre:border-border prose-pre:rounded-lg prose-strong:text-foreground prose-headings:text-foreground prose-a:text-signal prose-a:no-underline hover:prose-a:underline">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          pre(props) {
            return (
              <div className="relative group">
                <pre className="overflow-x-auto p-4 text-xs" {...props} />
                <button
                  onClick={() => {
                    const el = document.querySelector(".group pre");
                    if (el) navigator.clipboard.writeText(el.textContent || "");
                  }}
                  className="absolute top-2 right-2 px-2 py-1 text-[10px] bg-raised border border-border rounded opacity-0 group-hover:opacity-100 transition-opacity text-muted hover:text-foreground"
                >
                  Copy
                </button>
              </div>
            );
          },
          table(props) {
            return (
              <div className="overflow-x-auto border border-border rounded-lg my-3">
                <table className="w-full text-xs" {...props} />
              </div>
            );
          },
          thead(props) {
            return <thead className="bg-raised/50 border-b border-border" {...props} />;
          },
          th(props) {
            return <th className="px-3 py-2 text-left text-foreground font-semibold text-xs" {...props} />;
          },
          td(props) {
            return <td className="px-3 py-2 text-foreground/90 border-t border-border/30" {...props} />;
          },
          tr(props) {
            return <tr className="hover:bg-raised/30 transition-colors" {...props} />;
          },
          h1(props) {
            return <h1 className="text-xl font-bold text-foreground" {...props} />;
          },
          h2(props) {
            return <h2 className="text-lg font-bold text-foreground" {...props} />;
          },
          h3(props) {
            return <h3 className="text-base font-semibold text-foreground" {...props} />;
          },
          li(props) {
            return <li className="text-foreground/90" {...props} />;
          },
          p(props) {
            return <p className="text-foreground/90 leading-relaxed" {...props} />;
          },
          a(props) {
            return <a className="text-signal hover:underline" {...props} />;
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
