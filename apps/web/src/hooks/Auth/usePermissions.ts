"use client";

import { useCallback, useMemo } from "react";
import { useSession } from "./useSession";

// Reads the session's effective permission set and returns a membership check.
// The API always re-checks authoritatively; this only drives UI visibility.
export function usePermissions() {
  const { user, isLoading } = useSession();

  const set = useMemo(() => new Set(user?.effective ?? []), [user]);
  const has = useCallback((permission: string) => set.has(permission), [set]);

  return { has, isLoading, isSignedIn: !!user };
}
