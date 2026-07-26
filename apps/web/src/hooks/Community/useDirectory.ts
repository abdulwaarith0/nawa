"use client";

import { getApiClient } from "@/lib/apiClient";
import useSWR from "swr";

export interface DirectoryMember {
  id: string;
  handle: string;
  display_name_ar: string | null;
  display_name_en: string | null;
  headline_ar: string | null;
  headline_en: string | null;
  venture_name_ar: string | null;
  venture_name_en: string | null;
  sector: string | null;
  country: string | null;
  stage: string;
  skills: string[];
  domains: string[];
  is_mentor_eligible: boolean;
}

export interface DirectoryFilters {
  q?: string;
  domains?: string[];
  skills?: string[];
  sector?: string;
  country?: string;
  programId?: string;
  stage?: string;
  mentors?: boolean;
}

function buildQuery(filters: DirectoryFilters): string {
  const params = new URLSearchParams();
  if (filters.q) params.set("q", filters.q);
  for (const d of filters.domains ?? []) params.append("domains", d);
  for (const sk of filters.skills ?? []) params.append("skills", sk);
  if (filters.sector) params.set("sector", filters.sector);
  if (filters.country) params.set("country", filters.country);
  if (filters.programId) params.set("program_id", filters.programId);
  if (filters.stage) params.set("stage", filters.stage);
  if (filters.mentors) params.set("mentors", "true");
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

const fetchDirectory = (key: string) => getApiClient().get<DirectoryMember[]>(key);

// Searchable member directory (08-community-hub.md §3, `/community`).
export function useDirectory(filters: DirectoryFilters) {
  const key = `/community/directory${buildQuery(filters)}`;
  const { data, error, isLoading } = useSWR<DirectoryMember[]>(key, fetchDirectory, {
    revalidateOnFocus: false,
    shouldRetryOnError: false,
  });

  return { members: data, error, isLoading };
}
