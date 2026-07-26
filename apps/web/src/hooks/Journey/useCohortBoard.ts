"use client";

import { getApiClient } from "@/lib/apiClient";
import useSWR from "swr";

export interface BoardMilestone {
  id: string;
  sequence: number;
  title_ar: string | null;
  title_en: string | null;
  due_date: string | null;
  evidence_required: boolean;
}

export interface BoardMember {
  cohort_member_id: string;
  founder_profile_id: string;
  display_name_ar: string | null;
  display_name_en: string | null;
  handle: string;
}

export interface BoardCell {
  milestone_id: string;
  cohort_member_id: string;
  progress_id: string;
  status: string;
  overdue: boolean;
  evidence_links: Array<{ url: string; label: string; added_at: string }>;
}

export interface CohortBoard {
  milestones: BoardMilestone[];
  members: BoardMember[];
  cells: BoardCell[];
}

const fetchBoard = (key: string) => getApiClient().get<CohortBoard>(key);

// Program-manager grid (07-journey-copilot.md §2.1/§5): milestones as
// columns, cohort members as rows, one cell per pair.
export function useCohortBoard(cohortId: string | null) {
  const key = cohortId ? `/journey/cohorts/${cohortId}/board` : null;
  const { data, error, isLoading, mutate } = useSWR<CohortBoard>(key, fetchBoard, {
    revalidateOnFocus: false,
    shouldRetryOnError: false,
  });

  return { board: data, error, isLoading, refresh: mutate };
}
