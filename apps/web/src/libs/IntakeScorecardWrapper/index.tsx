"use client";

import {
  AiAttribution,
  Badge,
  Button,
  Callout,
  Card,
  CriterionCard,
  EmptyState,
  ErrorState,
  Loading,
} from "@/components";
import DecisionPanel, {
  type CohortOption,
  type DecisionSubmission,
} from "@/components/DecisionPanel";
import EligibilityProofPanel from "@/components/EligibilityProofPanel";
import { usePermissions } from "@/hooks/Auth";
import { useCohorts, useDecision, useResolveDedupMatch, useScorecard } from "@/hooks/Intake";
import { useLocale } from "@/i18n/LocaleProvider";
import { useT } from "@/i18n/useT";
import { ConsoleShell, Guard } from "@/layouts";
import { Routes } from "@nawa/contracts";
import { ArrowLeft, ScrollText } from "lucide-react";
import Link from "next/link";
import "./styles.css";

export interface IProps {
  applicationId: string;
}

// Scorecard + decision view (design-system §6.3.3, `/intake/applications/[id]`).
export default function IntakeScorecardWrapper({ applicationId }: IProps) {
  const t = useT("intake");
  const tAi = useT("ai");
  const locale = useLocale();
  const { has } = usePermissions();
  const { detail, error, isLoading, refresh } = useScorecard(applicationId);
  const decision = useDecision(applicationId);
  const resolveDedup = useResolveDedupMatch();
  const { cohorts, isLoading: cohortsLoading } = useCohorts(detail?.application.cycle_id ?? null);

  const cohortOptions: CohortOption[] = (cohorts ?? []).map((cohort) => ({
    id: cohort.id,
    label:
      (locale === "ar" ? cohort.name_ar : cohort.name_en) ??
      cohort.name_en ??
      cohort.name_ar ??
      cohort.id,
  }));

  async function handleDecision(input: DecisionSubmission) {
    await decision.run(input);
    refresh();
  }

  async function handleResolveDedup(matchId: string, status: "confirmed" | "dismissed") {
    await resolveDedup.run(matchId, status);
    refresh();
  }

  let body: React.ReactNode;
  if (isLoading) {
    body = <Loading />;
  } else if (error || !detail) {
    body = <ErrorState onRetry={() => refresh()} />;
  } else {
    const { application, scorecard, dedup_matches, documents, decisions, ai_band } = detail;
    body = (
      <>
        <Card className="nw-scorecard-header">
          <bdi dir="auto" className="nw-scorecard-name">
            {application.applicant_name}
          </bdi>
          <span className="nw-scorecard-email">{application.applicant_email}</span>
          {scorecard ? (
            <div className="nw-scorecard-overall">
              <div className="nw-scorecard-overall-head">
                <span className="nw-scorecard-overall-label">{t("scorecard.overallScore")}</span>
                <AiAttribution compact>{tAi("attribution.label")}</AiAttribution>
              </div>
              <div className="nw-scorecard-overall-value">{scorecard.total_score}</div>
            </div>
          ) : null}
          <Badge tone="neutral">
            {t("scorecard.sourceLanguage")}: {application.source_language}
          </Badge>
          {scorecard ? (
            <Badge tone="info">
              {t("scorecard.rubricVersion", { version: scorecard.rubric_version })}
            </Badge>
          ) : null}
        </Card>

        {!scorecard ? (
          <EmptyState
            headline={
              application.status === "normalize_failed"
                ? t("scorecard.scoringFailed")
                : t("scorecard.noScorecard")
            }
          />
        ) : (
          <>
            {scorecard.hidden_gem ? (
              <AiAttribution
                how={
                  locale === "ar" ? scorecard.hidden_gem_reason_ar : scorecard.hidden_gem_reason_en
                }
              >
                <strong>{t("scorecard.hiddenGem.title")}</strong>
                <p>{t("scorecard.hiddenGem.body")}</p>
              </AiAttribution>
            ) : null}

            <div className="nw-scorecard-criteria">
              {scorecard.criteria.map((criterion) => (
                <CriterionCard
                  key={criterion.criterion_key}
                  criterionKey={criterion.criterion_key}
                  score={criterion.score}
                  weight={criterion.weight}
                  rationaleAr={criterion.rationale_ar}
                  rationaleEn={criterion.rationale_en}
                  citations={criterion.citations}
                  originalAnswers={application.original_answers}
                  sourceLanguage={application.source_language}
                />
              ))}
            </div>
          </>
        )}

        <Card className="nw-scorecard-dedup">
          <h3>{t("scorecard.dedup.title")}</h3>
          {dedup_matches.length === 0 ? (
            <p className="nw-intake-subtitle">{t("scorecard.dedup.empty")}</p>
          ) : (
            dedup_matches.map((match) => (
              <div key={match.id} className="nw-scorecard-dedup-row">
                <AiAttribution compact>
                  {t("scorecard.dedup.similarity", { pct: Math.round(match.similarity * 100) })}
                </AiAttribution>
                <Badge
                  tone={
                    match.status === "confirmed"
                      ? "danger"
                      : match.status === "dismissed"
                        ? "neutral"
                        : "warning"
                  }
                >
                  {match.status}
                </Badge>
                <Link href={Routes.intake.application(match.matched_application_id)}>
                  {t("scorecard.dedup.viewApplication")}
                </Link>
                {match.status === "pending" && has("nawa:intake:override") ? (
                  <>
                    <Button
                      variant="secondary"
                      onClick={() => handleResolveDedup(match.id, "confirmed")}
                    >
                      {t("scorecard.dedup.confirm")}
                    </Button>
                    <Button
                      variant="ghost"
                      onClick={() => handleResolveDedup(match.id, "dismissed")}
                    >
                      {t("scorecard.dedup.dismiss")}
                    </Button>
                  </>
                ) : null}
              </div>
            ))
          )}
        </Card>

        <Card className="nw-scorecard-documents">
          <h3>{t("scorecard.documents.title")}</h3>
          {documents.length === 0 ? (
            <p className="nw-intake-subtitle">{t("scorecard.documents.empty")}</p>
          ) : (
            <ul>
              {documents.map((doc) => (
                <li key={doc.id}>{doc.file_name}</li>
              ))}
            </ul>
          )}
        </Card>

        {has("nawa:intake:override") ? (
          <Card className="nw-scorecard-decision">
            <h3>{t("decision.title")}</h3>
            <DecisionPanel
              aiBand={ai_band}
              isPending={decision.isPending}
              cohorts={cohortOptions}
              cohortsLoading={cohortsLoading}
              onSubmit={handleDecision}
            />
          </Card>
        ) : null}

        {has("nawa:intake:ingest") ? (
          <Card className="nw-scorecard-eligibility">
            <h3>{t("eligibility.title")}</h3>
            <EligibilityProofPanel applicationId={applicationId} onRecorded={refresh} />
          </Card>
        ) : null}

        <Card className="nw-scorecard-history">
          <h3>{t("scorecard.history.title")}</h3>
          {decisions.length === 0 ? (
            <p className="nw-intake-subtitle">{t("scorecard.history.empty")}</p>
          ) : (
            <ul>
              {decisions.map((d) => (
                <li key={d.id}>
                  {d.decision} — {new Date(d.created_at).toLocaleString(locale)}
                  {d.reason ? <Callout tone="info">{d.reason}</Callout> : null}
                </li>
              ))}
            </ul>
          )}
        </Card>
      </>
    );
  }

  return (
    <ConsoleShell>
      <div className="nw-shell">
        <div className="nw-page-head">
          <div>
            <div className="nw-page-eyebrow">{t("console.eyebrow")}</div>
            <h1 className="nw-page-title">{t("scorecard.title")}</h1>
          </div>
          <div className="nw-page-actions">
            <Link href={Routes.intake.home} className="nw-btn nw-btn-outline">
              <ArrowLeft size={15} aria-hidden="true" />
              {t("scorecard.backToConsole")}
            </Link>
            {has("nawa:audit:read") ? (
              <Link href={Routes.intake.audit} className="nw-btn nw-btn-secondary">
                <ScrollText size={15} aria-hidden="true" />
                {t("console.auditLog")}
              </Link>
            ) : null}
          </div>
        </div>
        <Guard permission="nawa:console:intake">{body}</Guard>
      </div>
    </ConsoleShell>
  );
}
