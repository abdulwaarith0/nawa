"use client";

import { getApiClient } from "@/lib/apiClient";
import useSWR from "swr";

export interface Citation {
  source: string;
  quote: string;
}

export interface ScorecardCriterion {
  criterion_key: string;
  score: number;
  weight: number;
  rationale_ar: string;
  rationale_en: string;
  citations: Citation[];
}

export interface Scorecard {
  id: string;
  rubric_id: string;
  rubric_version: number;
  prompt_version: string;
  source: string;
  total_score: number;
  confidence: number | null;
  rationale_ar: string;
  rationale_en: string;
  hidden_gem: boolean;
  hidden_gem_reason_ar: string | null;
  hidden_gem_reason_en: string | null;
  model: string | null;
  status: string;
  created_at: string;
  criteria: ScorecardCriterion[];
}

export interface ApplicationDetail {
  id: string;
  cycle_id: string;
  profile_id: string | null;
  applicant_name: string;
  applicant_email: string;
  source_language: string;
  title: string | null;
  summary: string | null;
  normalized: Record<string, unknown>;
  original_answers: Record<string, string>;
  status: string;
  ai_total_score: number | null;
  submitted_at: string;
  scored_at: string | null;
}

export interface DedupMatch {
  id: string;
  application_id: string;
  matched_application_id: string;
  similarity: number;
  status: "pending" | "confirmed" | "dismissed";
  reviewed_by: string | null;
  reviewed_at: string | null;
  created_at: string;
}

export interface ApplicationDocument {
  id: string;
  file_name: string;
  mime_type: string;
  kind: string;
  size_bytes: number;
  url: string | null;
  created_at: string;
}

export interface DecisionRecord {
  id: string;
  decided_by: string;
  decision: string;
  reason: string | null;
  previous_value: string | null;
  new_value: string | null;
  created_at: string;
}

export interface ScorecardDetail {
  application: ApplicationDetail;
  scorecard: Scorecard | null;
  scorecard_history: Scorecard[];
  dedup_matches: DedupMatch[];
  documents: ApplicationDocument[];
  decisions: DecisionRecord[];
  ai_band: "shortlist" | "waitlist" | "reject";
}

const fetchScorecard = (key: string) => getApiClient().get<ScorecardDetail>(key);

// SWR hook over the full scorecard read (design-system §6.3.3).
export function useScorecard(applicationId: string | null) {
  const key = applicationId ? `/intake/applications/${applicationId}/scorecard` : null;
  const { data, error, isLoading, mutate } = useSWR<ScorecardDetail>(key, fetchScorecard, {
    revalidateOnFocus: false,
    shouldRetryOnError: false,
  });

  return { detail: data, error, isLoading, refresh: mutate };
}
