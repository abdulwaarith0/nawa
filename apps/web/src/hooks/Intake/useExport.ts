"use client";

import { getApiClient } from "@/lib/apiClient";
import { useState } from "react";

export interface ExportResult {
  row_count: number;
  storage_key: string;
  url: string;
}

// Export-XLSX mutation (design-system §6.3.2, gated `nawa:intake:export`,
// rate-limited 5/min server-side). Opens the presigned URL once resolved —
// callers that want a custom affordance can ignore the return and window.open it themselves.
export function useExport(cycleId: string) {
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function run(): Promise<ExportResult> {
    setIsPending(true);
    setError(null);
    try {
      return await getApiClient().get<ExportResult>(`/intake/cycles/${cycleId}/export`);
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setIsPending(false);
    }
  }

  return { run, isPending, error };
}
