"use client";

import { getApiClient } from "@/lib/apiClient";
import { useState } from "react";

export type DedupResolution = "confirmed" | "dismissed";

// Dedup-match resolution mutation (design-system §6.3.3, gated
// `nawa:intake:override`). Resolving a match never changes the
// application's own status — that stays a separate decision.
export function useResolveDedupMatch() {
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function run(matchId: string, status: DedupResolution) {
    setIsPending(true);
    setError(null);
    try {
      return await getApiClient().patch<{ id: string; status: string; reviewed_by: string }>(
        `/intake/dedup-matches/${matchId}`,
        { status },
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
