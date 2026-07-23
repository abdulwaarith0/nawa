"use client";

import { getApiClient } from "@/lib/apiClient";
import useSWR from "swr";

export interface IamPolicy {
  id: string;
  name: string;
  description: string | null;
  statements: unknown[];
  managed: boolean;
}

const fetchPolicies = () => getApiClient().get<IamPolicy[]>("/iam/policies");

// SWR hook over the IAM policies list (design-system §6).
export function usePolicies() {
  const { data, error, isLoading, mutate } = useSWR<IamPolicy[]>("/iam/policies", fetchPolicies, {
    revalidateOnFocus: false,
    shouldRetryOnError: false,
  });

  return { policies: data, error, isLoading, refresh: mutate };
}
