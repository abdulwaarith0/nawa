"use client";

import { getApiClient } from "@/lib/apiClient";
import useSWR from "swr";

export interface TimelineItem {
  milestone_id: string;
  sequence: number;
  title_ar: string | null;
  title_en: string | null;
  description_ar: string | null;
  description_en: string | null;
  due_date: string | null;
  evidence_required: boolean;
  progress_id: string | null;
  status: string;
  note_ar: string | null;
  note_en: string | null;
  evidence_links: Array<{ url: string; label: string; added_at: string }>;
  overdue: boolean;
}

const fetchTimeline = (key: string) => getApiClient().get<TimelineItem[]>(key);

// Founder's own milestone timeline (07-journey-copilot.md §2.1/§5) — always
// the caller's own founder profile, resolved server-side from the session.
export function useMyTimeline(cohortId: string | null) {
  const key = cohortId ? `/journey/me/timeline?cohort_id=${cohortId}` : null;
  const { data, error, isLoading, mutate } = useSWR<TimelineItem[]>(key, fetchTimeline, {
    revalidateOnFocus: false,
    shouldRetryOnError: false,
  });

  return { items: data, error, isLoading, refresh: mutate };
}
