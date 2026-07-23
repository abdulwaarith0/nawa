"use client";

import { getApiClient } from "@/lib/apiClient";
import useSWR from "swr";

export interface AuditLog {
  id: string;
  actor_id: string | null;
  actor_type: string;
  action: string;
  target_type: string | null;
  target_id: string | null;
  status_code: number | null;
  duration_ms: number | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

const fetchAuditLogs = () => getApiClient().get<AuditLog[]>("/audit-logs");

// SWR hook over the audit log (design-system §6). Newest first, per the API.
export function useAuditLogs() {
  const { data, error, isLoading, mutate } = useSWR<AuditLog[]>("/audit-logs", fetchAuditLogs, {
    revalidateOnFocus: false,
    shouldRetryOnError: false,
  });

  return { logs: data, error, isLoading, refresh: mutate };
}
