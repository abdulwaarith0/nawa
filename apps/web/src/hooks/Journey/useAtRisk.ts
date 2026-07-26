"use client";

import { getApiClient } from "@/lib/apiClient";
import useSWR from "swr";

export interface AtRiskEntry {
  progress_id: string;
  milestone_id: string;
  founder_profile_id: string;
  status: string;
  due_date: string | null;
  reasons: string[];
}

const fetchAtRisk = (key: string) => getApiClient().get<AtRiskEntry[]>(key);

// At-risk rail (07-journey-copilot.md §2.1/§4.2): overdue or blocked progress
// rows, each carrying machine-readable reasons (`overdue:<id>`, `blocked:<id>`).
export function useAtRisk(cohortId: string | null) {
  const key = cohortId ? `/journey/cohorts/${cohortId}/at-risk` : null;
  const { data, error, isLoading, mutate } = useSWR<AtRiskEntry[]>(key, fetchAtRisk, {
    revalidateOnFocus: false,
    shouldRetryOnError: false,
  });

  return { atRisk: data, error, isLoading, refresh: mutate };
}
