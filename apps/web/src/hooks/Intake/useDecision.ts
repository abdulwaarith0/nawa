"use client";

import { getApiClient } from "@/lib/apiClient";
import { useState } from "react";

export type DecisionChoice = "shortlist" | "waitlist" | "reject" | "accept";

export interface DecisionInput {
  decision: DecisionChoice;
  reason?: string;
  cohortId?: string;
}

export interface DecisionResult {
  decision_id: string;
  application_id: string;
  status: string;
  decision: string;
  ai_band: string;
  overridden: boolean;
  profile_id: string | null;
}

// Decision-panel mutation (design-system §6.3.3, gated `nawa:intake:override`).
// A reason is required (client + server) whenever the choice diverges from
// the AI recommendation band — enforced here by simply always sending
// whatever reason the caller supplied; the server is the authority on
// whether it was actually required.
export function useDecision(applicationId: string) {
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function run(input: DecisionInput): Promise<DecisionResult> {
    setIsPending(true);
    setError(null);
    try {
      return await getApiClient().post<DecisionResult>(
        `/intake/applications/${applicationId}/decision`,
        {
          decision: input.decision,
          reason: input.reason ?? null,
          cohort_id: input.cohortId ?? null,
        },
      );
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setIsPending(false);
    }
  }

  return { run, isPending, error };
}
