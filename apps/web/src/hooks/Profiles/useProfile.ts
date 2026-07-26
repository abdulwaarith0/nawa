"use client";

import { getApiClient } from "@/lib/apiClient";
import useSWR from "swr";
import type { ProgramHistoryEntry } from "./useProgramHistory";

export interface ProfileAsk {
  kind: string;
  text_ar: string | null;
  text_en: string | null;
  active: boolean;
}

export interface ProfileDetail {
  handle: string;
  display_name_ar: string | null;
  display_name_en: string | null;
  headline_ar: string | null;
  headline_en: string | null;
  bio_ar: string | null;
  bio_en: string | null;
  venture_name_ar: string | null;
  venture_name_en: string | null;
  venture_summary_ar: string | null;
  venture_summary_en: string | null;
  stage: string;
  sector: string | null;
  country: string | null;
  city: string | null;
  website: string | null;
  links: Array<{ label: string; url: string }>;
  skills: string[];
  domains: string[];
  is_mentor_eligible: boolean;
  kpi_snapshot: Record<string, unknown>;
  kpi_snapshot_at: string | null;
  program_history: ProgramHistoryEntry[];
  asks: ProfileAsk[];
}

const fetchProfile = (key: string) => getApiClient().get<ProfileDetail>(key);

// Public founder profile view (08-community-hub.md §2, `/profile/[handle]`).
export function useProfile(handle: string | null) {
  const key = handle ? `/profiles/${handle}` : null;
  const { data, error, isLoading } = useSWR<ProfileDetail>(key, fetchProfile, {
    revalidateOnFocus: false,
    shouldRetryOnError: false,
  });

  return { profile: data, error, isLoading };
}
