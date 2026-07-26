"use client";

import { getApiClient } from "@/lib/apiClient";
import { useState } from "react";

// Founder-drivable statuses only — schema rejects done/blocked/waived
// server-side (07-journey-copilot.md §2.1); this type mirrors that on purpose.
export type FounderProgressStatus = "not_started" | "in_progress" | "submitted";

export interface UpdateProgressInput {
  status?: FounderProgressStatus;
  noteAr?: string;
  noteEn?: string;
  evidenceLinks?: Array<{ url: string; label: string; added_at: string }>;
}

export interface ProgressResult {
  id: string;
  milestone_id: string;
  status: string;
  note_ar: string | null;
  note_en: string | null;
  evidence_links: Array<{ url: string; label: string; added_at: string }>;
}

// Founder progress mutation (gated `nawa:journey:progress` + ownership —
// PATCHing another member's progress id 404s, never 403, per the canon
// never-confirm-foreign-ids rule).
export function useUpdateProgress(progressId: string) {
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function run(input: UpdateProgressInput): Promise<ProgressResult> {
    setIsPending(true);
    setError(null);
    try {
      return await getApiClient().patch<ProgressResult>(`/journey/progress/${progressId}`, {
        status: input.status,
        note_ar: input.noteAr,
        note_en: input.noteEn,
        evidence_links: input.evidenceLinks,
      });
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setIsPending(false);
    }
  }

  return { run, isPending, error };
}
