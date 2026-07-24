"use client";

import { getApiClient } from "@/lib/apiClient";
import useSWR from "swr";

export interface ShortlistCriterionScore {
  criterion_key: string;
  score: number;
  weight: number;
}

export interface ShortlistRow {
  rank: number;
  application_id: string;
  applicant_name: string;
  title: string | null;
  language: string;
  country: string | null;
  total_score: number | null;
  criteria: ShortlistCriterionScore[];
  hidden_gem: boolean;
  dedup_pending: boolean;
  normalize_failed: boolean;
  status: string;
  decision: "undecided" | "shortlist" | "waitlist" | "reject" | "accept" | "decided";
}

export interface ShortlistFilters {
  scoreBand?: string;
  criterion?: string;
  criterionMin?: number;
  flags?: string[];
  language?: string;
  country?: string;
  decision?: string;
  q?: string;
  limit?: number;
  offset?: number;
}

function buildQuery(filters: ShortlistFilters): string {
  const params = new URLSearchParams();
  if (filters.scoreBand) params.set("score_band", filters.scoreBand);
  if (filters.criterion) params.set("criterion", filters.criterion);
  if (filters.criterionMin !== undefined) params.set("criterion_min", String(filters.criterionMin));
  if (filters.flags && filters.flags.length > 0) params.set("flags", filters.flags.join(","));
  if (filters.language) params.set("language", filters.language);
  if (filters.country) params.set("country", filters.country);
  if (filters.decision) params.set("decision", filters.decision);
  if (filters.q) params.set("q", filters.q);
  if (filters.limit !== undefined) params.set("limit", String(filters.limit));
  if (filters.offset !== undefined) params.set("offset", String(filters.offset));
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

const fetchShortlist = (key: string) => getApiClient().get<ShortlistRow[]>(key);

// SWR hook over the ranked shortlist (design-system §6.3.2). Every filter is
// combinable, matching the API exactly — no client-side re-filtering.
export function useShortlist(cycleId: string | null, filters: ShortlistFilters = {}) {
  const key = cycleId ? `/intake/cycles/${cycleId}/shortlist${buildQuery(filters)}` : null;
  const { data, error, isLoading, mutate } = useSWR<ShortlistRow[]>(key, fetchShortlist, {
    revalidateOnFocus: false,
    shouldRetryOnError: false,
  });

  return { rows: data, error, isLoading, refresh: mutate };
}
