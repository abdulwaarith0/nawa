"use client";

import Button from "@/components/Button";
import Callout from "@/components/Callout";
import Input from "@/components/Input";
import { useT } from "@/i18n/useT";
import { useMemo, useState } from "react";
import "./styles.css";

export type DecisionChoice = "shortlist" | "waitlist" | "reject" | "accept";

export interface DecisionSubmission {
  decision: DecisionChoice;
  reason?: string;
  cohortId?: string;
}

export interface IProps {
  aiBand: "shortlist" | "waitlist" | "reject";
  isPending?: boolean;
  onSubmit: (input: DecisionSubmission) => void;
}

// Diverges from the AI recommendation the same way the backend's
// `decide_application` service does: "accept" only diverges when the band
// is waitlist/reject (accepting a shortlist-band applicant is advancing the
// AI's own call, not overriding it) — every other decision diverges whenever
// it differs from the band outright.
function diverges(decision: DecisionChoice, aiBand: string): boolean {
  if (decision === "accept") return aiBand !== "shortlist";
  return decision !== aiBand;
}

// The four-action decision panel (design-system §6.3.3, gated
// `nawa:intake:override`). A reason becomes required — client AND server —
// the moment the chosen decision diverges from the AI band.
export default function DecisionPanel({ aiBand, isPending = false, onSubmit }: IProps) {
  const t = useT("intake");
  const [decision, setDecision] = useState<DecisionChoice | null>(null);
  const [reason, setReason] = useState("");
  const [cohortId, setCohortId] = useState("");
  const [touched, setTouched] = useState(false);

  const reasonRequired = useMemo(
    () => (decision ? diverges(decision, aiBand) : false),
    [decision, aiBand],
  );
  const reasonMissing = reasonRequired && reason.trim().length === 0;
  const cohortMissing = decision === "accept" && cohortId.trim().length === 0;
  const canSubmit = decision !== null && !reasonMissing && !cohortMissing;

  function handleSubmit() {
    setTouched(true);
    if (!canSubmit || decision === null) return;
    onSubmit({
      decision,
      reason: reason.trim() || undefined,
      cohortId: decision === "accept" ? cohortId.trim() : undefined,
    });
  }

  return (
    <div className="nw-decision-panel">
      <p className="nw-decision-band">
        {t("decision.aiBand", { band: t(`shortlist.decisionStates.${aiBand}`) })}
      </p>
      <div className="nw-decision-actions">
        {(["shortlist", "waitlist", "reject", "accept"] as DecisionChoice[]).map((choice) => (
          <Button
            key={choice}
            variant={decision === choice ? "primary" : "secondary"}
            onClick={() => setDecision(choice)}
            disabled={isPending}
          >
            {t(`decision.actions.${choice}`)}
          </Button>
        ))}
      </div>
      {decision === "accept" ? (
        <Input
          label={t("decision.cohortLabel")}
          value={cohortId}
          onChange={(event) => setCohortId(event.target.value)}
          error={touched && cohortMissing ? t("decision.cohortRequired") : undefined}
        />
      ) : null}
      {reasonRequired ? <Callout tone="info">{t("decision.reasonRequired")}</Callout> : null}
      {decision !== null ? (
        <Input
          label={t("decision.reasonLabel")}
          placeholder={t("decision.reasonPlaceholder")}
          value={reason}
          onChange={(event) => setReason(event.target.value)}
          dirAuto
          error={touched && reasonMissing ? t("decision.reasonRequired") : undefined}
        />
      ) : null}
      <Button onClick={handleSubmit} loading={isPending} disabled={decision === null}>
        {isPending ? t("decision.submitting") : t("decision.submit")}
      </Button>
    </div>
  );
}
