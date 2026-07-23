"use client";

import { getApiClient } from "@/lib/apiClient";
import useSWR from "swr";

export type SiteConfig = Record<string, unknown>;

const fetchSiteConfig = () => getApiClient().get<SiteConfig>("/admin/site-config");

// SWR hook over the admin site configuration (design-system §6).
export function useSiteConfig() {
  const { data, error, isLoading, mutate } = useSWR<SiteConfig>(
    "/admin/site-config",
    fetchSiteConfig,
    { revalidateOnFocus: false, shouldRetryOnError: false },
  );

  return { config: data, error, isLoading, refresh: mutate };
}
