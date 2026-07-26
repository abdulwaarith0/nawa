"use client";

import { getApiClient } from "@/lib/apiClient";
import { useState } from "react";

// Manager-owned transitions only (07-journey-copilot.md §2.1): submitted ->
// done, any -> blocked/waived (note required server-side), done -> submitted
// (reopen).
export type ReviewStatus = "submitted" | "done" | "blocked" | "waived";

export interface ReviewProgressInput {
  status: ReviewStatus;
  noteAr?: string;
  noteEn?: string;
}

export interface ReviewResult {
  id: string;
  milestone_id: string;
  status: string;
  note_ar: string | null;
  note_en: string | null;
  reviewed_by_user_id: string | null;
}

// Manager progress review mutation (gated `nawa:journey:manage`).
export function useReviewProgress(progressId: string) {
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function run(input: ReviewProgressInput): Promise<ReviewResult> {
    setIsPending(true);
    setError(null);
    try {
      return await getApiClient().patch<ReviewResult>(`/journey/progress/${progressId}/review`, {
        status: input.status,
        note_ar: input.noteAr,
        note_en: input.noteEn,
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
