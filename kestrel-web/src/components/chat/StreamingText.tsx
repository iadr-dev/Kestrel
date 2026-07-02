"use client";

import { useEffect, useRef, useState } from "react";

/** Live streaming answer text with a claude.ai-style gradual reveal.
 *
 *  Full markdown is re-parsed on every token and would (a) be costly and (b) flicker
 *  on half-formed syntax, so during streaming we render plain text and only animate
 *  the NEWLY arrived tail: the already-shown prefix stays static while each fresh
 *  chunk fades+blurs in via `.stream-chunk`. The finalized message later renders as
 *  full markdown (MessageBubble), so formatting is preserved once complete. */
export function StreamingText({ text }: { text: string }) {
  const prevRef = useRef("");
  const [head, setHead] = useState("");
  const [tail, setTail] = useState("");

  useEffect(() => {
    const prev = prevRef.current;
    if (text.startsWith(prev)) {
      // Normal append: freeze the old text as head, animate the new delta as tail.
      setHead(prev);
      setTail(text.slice(prev.length));
    } else {
      // Non-append change (reset/replace) — show all at once.
      setHead(text);
      setTail("");
    }
    prevRef.current = text;
  }, [text]);

  return (
    <span className="whitespace-pre-wrap break-words text-foreground/90 leading-relaxed">
      {head}
      {tail && (
        // key on length so each new tail remounts and re-runs the fade animation
        <span key={head.length} className="stream-chunk">{tail}</span>
      )}
    </span>
  );
}
