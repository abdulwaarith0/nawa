"use client";

import { getApiClient } from "@/lib/apiClient";
import useSWR from "swr";

export interface JourneyCohort {
  id: string;
  program_name_en: string | null;
  program_name_ar: string | null;
  // Short chip label, e.g. "SoS · Season 18". Backend may derive it.
  label_en: string | null;
  label_ar: string | null;
  // Human round descriptor, e.g. "12-week prototyping round".
  round_en: string | null;
  round_ar: string | null;
  member_count: number;
}

const fetchCohorts = (key: string) => getApiClient().get<JourneyCohort[]>(key);

// The cohorts the current user can track, for the Journey cohort picker.
// Backend contract (to be built):
//   GET /journey/cohorts -> JourneyCohort[]
// (resolves cohorts across cycles the user manages/belongs to — the current
// board picker only saw the active cycle's first cohort, so seeded cohorts
// under historical cycles never surfaced.)
export function useJourneyCohorts() {
  const { data, error, isLoading, mutate } = useSWR<JourneyCohort[]>(
    "/journey/cohorts",
    fetchCohorts,
    { revalidateOnFocus: false, shouldRetryOnError: false },
  );

  return { cohorts: data ?? [], error, isLoading, refresh: mutate };
}
