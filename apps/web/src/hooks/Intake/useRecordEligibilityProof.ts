"use client";

import { getApiClient } from "@/lib/apiClient";
import { useState } from "react";

export type EligibilityVerdict = "eligible" | "ineligible";

export interface EligibilityProofInput {
  contractAddress: string;
  txId: string;
  verdict: EligibilityVerdict;
  network?: string;
  minAge?: number | null;
  maxPriorFunding?: number | null;
}

export interface EligibilityProofResult {
  application_id: string;
  proof_ref: string;
  verdict: string;
  network: string;
}

// Attaches a Midnight zero-knowledge eligibility proof reference to an
// application (gated `nawa:intake:ingest`). The proof is generated client-side
// by the midnight-eligibility contract; only the verifiable reference (contract
// address + tx id) and the verdict are sent — the server records them in the
// immutable audit log. The applicant's age and funding never reach NAWA.
export function useRecordEligibilityProof(applicationId: string) {
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function run(input: EligibilityProofInput): Promise<EligibilityProofResult> {
    setIsPending(true);
    setError(null);
    try {
      return await getApiClient().post<EligibilityProofResult>(
        `/intake/applications/${applicationId}/eligibility-proof`,
        {
          contract_address: input.contractAddress,
          tx_id: input.txId,
          verdict: input.verdict,
          network: input.network ?? "undeployed",
          min_age: input.minAge ?? null,
          max_prior_funding: input.maxPriorFunding ?? null,
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
