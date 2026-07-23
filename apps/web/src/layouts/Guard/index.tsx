"use client";

import { EmptyState, Loading } from "@/components";
import { usePermissions } from "@/hooks/Auth";
import { useT } from "@/i18n/useT";
import type { ReactNode } from "react";

export interface IProps {
  permission: string;
  children: ReactNode;
}

// Client-side visibility gate. Renders a loading state while the session
// resolves, a localized "no access" empty state when the permission is absent,
// and the children when it is held. The API still re-checks authoritatively —
// this only prevents rendering a surface the user cannot use.
export default function Guard({ permission, children }: IProps) {
  const { has, isLoading } = usePermissions();
  const t = useT("console");

  if (isLoading) return <Loading />;
  if (!has(permission)) {
    return <EmptyState headline={t("states.deniedTitle")} description={t("states.deniedBody")} />;
  }
  return <>{children}</>;
}
