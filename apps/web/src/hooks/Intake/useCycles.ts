"use client";

import { getApiClient } from "@/lib/apiClient";
import useSWR from "swr";

export interface IntakeCycle {
  id: string;
  program_id: string;
  program_name_ar: string | null;
  program_name_en: string | null;
  name_ar: string | null;
  name_en: string | null;
  status: string;
  opens_at: string | null;
  closes_at: string | null;
}

const fetchCycles = () => getApiClient().get<IntakeCycle[]>("/intake/cycles");

// SWR hook over the intake cycle picker (design-system §6.3.1).
export function useCycles() {
  const { data, error, isLoading, mutate } = useSWR<IntakeCycle[]>("/intake/cycles", fetchCycles, {
    revalidateOnFocus: false,
    shouldRetryOnError: false,
  });

  return { cycles: data, error, isLoading, refresh: mutate };
}
