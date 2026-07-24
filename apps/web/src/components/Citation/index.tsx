"use client";

import AiAttribution from "@/components/AiAttribution";
import Bidi from "@/components/Bidi";
import { useMemo } from "react";
import "./styles.css";

export interface IProps {
  text: string;
  quote: string;
  lang?: string;
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

// Locates `quote` inside `text` tolerating whitespace differences (runs of
// whitespace in the quote match any run of whitespace in the source) — the
// same normalization rule the backend's verbatim-citation check uses
// (services/intake/_citations.py's `_normalize_ws`), so a citation the
// backend accepted always locates here too.
function locateQuote(text: string, quote: string): { start: number; end: number } | null {
  const trimmed = quote.trim();
  if (!trimmed) return null;
  const pattern = escapeRegExp(trimmed).replace(/\s+/g, "\\s+");
  const match = new RegExp(pattern).exec(text);
  if (!match) return null;
  return { start: match.index, end: match.index + match[0].length };
}

// Renders `text` with `quote` highlighted in situ (design-system §6.3.3) — the
// reader sees the AI's cited evidence inside the applicant's own verbatim
// answer, in its original source language and direction, rather than a
// disconnected excerpt. Falls back to plain text if the quote can't be
// located (a malformed/stale citation should never crash the scorecard view).
export default function Citation({ text, quote, lang }: IProps) {
  return useMemo(() => {
    const location = locateQuote(text, quote);
    if (!location) {
      return (
        <Bidi lang={lang}>
          <span className="nw-citation-text">{text}</span>
        </Bidi>
      );
    }
    const before = text.slice(0, location.start);
    const matched = text.slice(location.start, location.end);
    const after = text.slice(location.end);
    return (
      <Bidi lang={lang}>
        <span className="nw-citation-text">
          {before}
          <AiAttribution compact>{matched}</AiAttribution>
          {after}
        </span>
      </Bidi>
    );
  }, [text, quote, lang]);
}
