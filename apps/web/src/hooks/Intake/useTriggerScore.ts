"use client";

import { getApiClient } from "@/lib/apiClient";
import { useState } from "react";

// Trigger-scoring mutation (design-system §6.3.1, gated `nawa:intake:score`).
export function useTriggerScore(cycleId: string) {
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function run(rescore = false): Promise<{ cycle_id: string }> {
    setIsPending(true);
    setError(null);
    try {
      const qs = rescore ? "?rescore=true" : "";
      return await getApiClient().post<{ cycle_id: string }>(
        `/intake/cycles/${cycleId}/score${qs}`,
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
