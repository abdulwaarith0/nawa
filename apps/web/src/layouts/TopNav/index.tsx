"use client";

import { Avatar } from "@/components";
import { useSession } from "@/hooks/Auth";
import { useT } from "@/i18n/useT";
import LocaleSwitcher from "@/layouts/LocaleSwitcher";
import { getApiClient } from "@/lib/apiClient";
import { Routes } from "@nawa/contracts";
import { useCallback, useMemo } from "react";
import "./styles.css";

// TopNav shell (design-system §7): sticky top bar with the NAWA wordmark at
// inline-start, the locale switcher + avatar/auth actions at inline-end. Signed
// out shows Sign in + a primary Apply; signed in shows the member's avatar and
// a sign-out action.
export default function TopNav() {
  const { user, isSignedIn } = useSession();
  const t = useT("common");

  const onSignOut = useCallback(async () => {
    try {
      await getApiClient().auth.logout();
    } finally {
      window.location.assign(Routes.home);
    }
  }, []);

  return useMemo(
    () => (
      <header className="nw-topnav">
        <a href={Routes.home} className="nw-wordmark nw-display" lang="en">
          NAWA
        </a>
        <div className="nw-topnav-end">
          <LocaleSwitcher />
          {isSignedIn && user ? (
            <>
              <a href={Routes.dashboard} className="nw-btn nw-btn-ghost">
                {t("actions.dashboard")}
              </a>
              <a
                href={Routes.profile(user.username)}
                className="nw-topnav-avatar"
                aria-label={user.full_name}
              >
                <Avatar name={user.full_name} size={32} />
              </a>
              <button type="button" className="nw-btn nw-btn-ghost" onClick={onSignOut}>
                {t("actions.signOut")}
              </button>
            </>
          ) : (
            <>
              <a href={Routes.login} className="nw-btn nw-btn-ghost">
                {t("actions.signIn")}
              </a>
              <a href={Routes.requestAccess} className="nw-btn nw-btn-primary">
                {t("actions.apply")}
              </a>
            </>
          )}
        </div>
      </header>
    ),
    [user, isSignedIn, onSignOut, t],
  );
}
