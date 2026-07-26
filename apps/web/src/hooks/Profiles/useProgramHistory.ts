"use client";

import { getApiClient } from "@/lib/apiClient";
import useSWR from "swr";

export interface ProgramHistoryEntry {
  cohort_id: string;
  cohort_name_ar: string | null;
  cohort_name_en: string | null;
  cycle_id: string;
  cycle_name_ar: string | null;
  cycle_name_en: string | null;
  program_id: string;
  program_name_ar: string | null;
  program_name_en: string | null;
  role: string;
  status: string;
  starts_at: string;
}

const fetchProgramHistory = () =>
  getApiClient().get<ProgramHistoryEntry[]>("/profiles/me/program-history");

// "Which programs am I in" — the founder's own cohort memberships, newest
// first. The Journey timeline uses this to resolve which cohort_id to load
// (there's no dedicated "my cohorts" route; this is that route in practice).
export function useProgramHistory() {
  const { data, error, isLoading } = useSWR<ProgramHistoryEntry[]>(
    "/profiles/me/program-history",
    fetchProgramHistory,
    { revalidateOnFocus: false, shouldRetryOnError: false },
  );

  return { history: data, error, isLoading };
}
