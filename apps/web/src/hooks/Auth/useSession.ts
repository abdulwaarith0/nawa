"use client";

import { getApiClient } from "@/lib/apiClient";
import useSWR from "swr";

// The current user's session (design-system §6: client data flows through SWR
// hooks that call the typed api-client). Returns null when signed out.
export interface SessionUser {
  id: string;
  email: string;
  username: string;
  full_name: string;
  language: "ar" | "en";
  is_active: boolean;
  effective: string[];
}

async function fetchMe(): Promise<SessionUser | null> {
  try {
    return await getApiClient().get<SessionUser>("/auth/me");
  } catch {
    return null;
  }
}

export function useSession() {
  const { data, error, isLoading, mutate } = useSWR<SessionUser | null>("/auth/me", fetchMe, {
    revalidateOnFocus: false,
    shouldRetryOnError: false,
  });

  return {
    user: data ?? null,
    isLoading,
    isSignedIn: !!data,
    error,
    refresh: mutate,
  };
}
