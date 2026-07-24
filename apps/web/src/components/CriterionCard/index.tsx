"use client";

import Card from "@/components/Card";
import Citation from "@/components/Citation";
import { useLocale } from "@/i18n/LocaleProvider";
import { useMemo } from "react";
import "./styles.css";

export interface CriterionCardCitation {
  source: string;
  quote: string;
}

export interface IProps {
  criterionKey: string;
  score: number;
  weight: number;
  rationaleAr: string;
  rationaleEn: string;
  citations: CriterionCardCitation[];
  originalAnswers: Record<string, string>;
  sourceLanguage?: string;
}

function sourceText(source: string, originalAnswers: Record<string, string>): string | null {
  if (!source.startsWith("answer:")) return null;
  return originalAnswers[source.slice("answer:".length)] ?? null;
}

// One rubric criterion's AI scorecard entry (design-system §6.3.3): score,
// weight, bilingual rationale in the current UI locale, and every citation
// rendered in situ inside the original answer it quotes. Citations pointing
// at a document (not an answer) render as a plain quote — document text
// isn't available on this DTO.
export default function CriterionCard({
  criterionKey,
  score,
  weight,
  rationaleAr,
  rationaleEn,
  citations,
  originalAnswers,
  sourceLanguage,
}: IProps) {
  const locale = useLocale();
  const rationale = locale === "ar" ? rationaleAr : rationaleEn;

  return useMemo(
    () => (
      <Card className="nw-criterion-card">
        <div className="nw-criterion-header">
          <span className="nw-criterion-key">{criterionKey.replace(/_/g, " ")}</span>
          <span className="nw-criterion-score">{score}</span>
          <span className="nw-criterion-weight">×{weight}</span>
        </div>
        <p className="nw-criterion-rationale">{rationale}</p>
        {citations.length > 0 ? (
          <ul className="nw-criterion-citations">
            {citations.map((citation) => {
              const text = sourceText(citation.source, originalAnswers);
              return (
                <li key={`${citation.source}:${citation.quote}`}>
                  {text ? (
                    <Citation text={text} quote={citation.quote} lang={sourceLanguage} />
                  ) : (
                    <span className="nw-criterion-citation-fallback">“{citation.quote}”</span>
                  )}
                </li>
              );
            })}
          </ul>
        ) : null}
      </Card>
    ),
    [criterionKey, score, weight, rationale, citations, originalAnswers, sourceLanguage],
  );
}
