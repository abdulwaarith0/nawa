"use client";

import { getApiClient } from "@/lib/apiClient";
import { useState } from "react";

export interface UploadResult {
  upload_id: string;
  row_count: number;
}

// Multipart bulk-upload mutation (design-system §6.3.1). `columnMap` maps
// source spreadsheet columns to canonical fields / question keys, per
// 06-intake-copilot.md §2.1 — sent as a JSON-encoded form field alongside
// the file since multipart has no native nested-object support.
export function useUpload(cycleId: string) {
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function run(file: File, columnMap: Record<string, string>): Promise<UploadResult> {
    setIsPending(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("column_map", JSON.stringify(columnMap));
      return await getApiClient().post<UploadResult>(`/intake/cycles/${cycleId}/uploads`, form);
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setIsPending(false);
    }
  }

  return { run, isPending, error };
}
