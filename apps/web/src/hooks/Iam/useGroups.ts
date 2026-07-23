"use client";

import { getApiClient } from "@/lib/apiClient";
import useSWR from "swr";

export interface IamGroup {
  id: string;
  name: string;
  description: string | null;
  policy_ids: string[];
  inline_statements: unknown[];
  managed: boolean;
}

const fetchGroups = () => getApiClient().get<IamGroup[]>("/iam/groups");

// SWR hook over the IAM groups list (design-system §6). Errors surface to the
// caller so the surface can render its error state.
export function useGroups() {
  const { data, error, isLoading, mutate } = useSWR<IamGroup[]>("/iam/groups", fetchGroups, {
    revalidateOnFocus: false,
    shouldRetryOnError: false,
  });

  return { groups: data, error, isLoading, refresh: mutate };
}
