"use client";

import { getApiClient } from "@/lib/apiClient";
import useSWR from "swr";
import type { AuditLog } from "./useAuditLogs";

const INTAKE_TARGET_TYPES = ["intake_cycle", "intake_application", "dedup_match"] as const;

async function fetchIntakeAuditLogs(): Promise<AuditLog[]> {
  const client = getApiClient();
  const pages = await Promise.all(
    INTAKE_TARGET_TYPES.map((targetType) =>
      client.get<AuditLog[]>(`/audit-logs?target_type=${targetType}`),
    ),
  );
  return pages
    .flat()
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
}

// GET /audit-logs filters by a single target_type per call, so an
// intake-scoped view fans out over the three target types intake actions are
// recorded against (score runs on intake_cycle, decisions on
// intake_application, dedup resolutions on dedup_match) and merges them
// client-side, newest first.
export function useIntakeAuditLogs() {
  const { data, error, isLoading, mutate } = useSWR<AuditLog[]>(
    "/audit-logs:intake",
    fetchIntakeAuditLogs,
    { revalidateOnFocus: false, shouldRetryOnError: false },
  );

  return { logs: data, error, isLoading, refresh: mutate };
}
