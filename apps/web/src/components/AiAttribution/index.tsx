"use client";

import { useT } from "@/i18n/useT";
import { type ReactNode, useMemo } from "react";
import "./styles.css";

export interface IProps {
  children: ReactNode;
  how?: ReactNode;
  compact?: boolean;
}

// The universal AI marker (§10). Everything the machine wrote/scored/flagged is
// wrapped in this: amber border + tint, a sparkle glyph (never flipped), the
// localized "AI-generated" label, and an optional "How was this produced?"
// disclosure. Color is never the only cue — the sparkle pairs with real text
// so attribution survives grayscale and colour-blindness. Nothing AI-produced
// renders outside this wrapper. `compact` renders a small inline pill (sparkle
// + children only, no label/disclosure block) for dense contexts like a
// shortlist table cell — this stays the ONLY component that touches amber
// tokens, rather than a second inline badge introducing them elsewhere.
export default function AiAttribution({ children, how, compact = false }: IProps) {
  const t = useT("ai");

  return useMemo(() => {
    if (compact) {
      return (
        <span
          className="nw-ai-attribution nw-ai-attribution-compact"
          title={t("attribution.label")}
        >
          <span className="nw-ai-sparkle" aria-hidden="true">
            ✦
          </span>
          {children}
        </span>
      );
    }
    return (
      <div className="nw-ai-attribution">
        <span className="nw-ai-label">
          <span className="nw-ai-sparkle" aria-hidden="true">
            ✦
          </span>
          {t("attribution.label")}
        </span>
        <div className="nw-ai-body">{children}</div>
        {how ? (
          <details className="nw-ai-how">
            <summary>{t("attribution.how")}</summary>
            <div>{how}</div>
          </details>
        ) : null}
      </div>
    );
  }, [children, how, compact, t]);
}
