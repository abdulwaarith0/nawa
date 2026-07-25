"use client";

import { getApiClient } from "@/lib/apiClient";
import useSWR from "swr";

export interface IntakeCohort {
  id: string;
  name_ar: string | null;
  name_en: string | null;
  starts_at: string;
  ends_at: string | null;
}

const fetchCohorts = (key: string) => getApiClient().get<IntakeCohort[]>(key);

// Cohort picker for the accept-decision panel (06-intake-copilot.md §6.2) —
// scoped to the application's own cycle, matching the backend's own
// cohort.cycle_id check in decide_application.
export function useCohorts(cycleId: string | null) {
  const key = cycleId ? `/intake/cycles/${cycleId}/cohorts` : null;
  const { data, error, isLoading } = useSWR<IntakeCohort[]>(key, fetchCohorts, {
    revalidateOnFocus: false,
    shouldRetryOnError: false,
  });

  return { cohorts: data, error, isLoading };
}
