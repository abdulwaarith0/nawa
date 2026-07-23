"use client";

import { useT } from "@/i18n/useT";
import { type ReactNode, useMemo } from "react";
import "./styles.css";

export interface IProps {
  children: ReactNode;
  how?: ReactNode;
}

// The universal AI marker (§10). Everything the machine wrote/scored/flagged is
// wrapped in this: amber border + tint, a sparkle glyph (never flipped), the
// localized "AI-generated" label, and an optional "How was this produced?"
// disclosure. Color is never the only cue — the sparkle pairs with real text
// so attribution survives grayscale and colour-blindness. Nothing AI-produced
// renders outside this wrapper.
export default function AiAttribution({ children, how }: IProps) {
  const t = useT("ai");

  return useMemo(
    () => (
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
    ),
    [children, how, t],
  );
}
