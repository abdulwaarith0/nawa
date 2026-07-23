"use client";

import { Routes } from "@nawa/contracts";
import { useSession } from "../../hooks/useSession";
import { useT } from "../../i18n/useT";
import { getApiClient } from "../../lib/apiClient";
import { Avatar } from "../ui/Avatar";
import { LocaleSwitcher } from "./LocaleSwitcher";

// TopNav shell (design-system §7): sticky top bar with the NAWA wordmark at
// inline-start, the locale switcher + avatar/auth actions at inline-end. Signed
// out shows Sign in + a primary Apply; signed in shows the member's avatar and
// a sign-out action.
export function TopNav() {
  const { user, isSignedIn } = useSession();
  const t = useT("common");

  async function onSignOut() {
    try {
      await getApiClient().auth.logout();
    } finally {
      window.location.assign(Routes.home);
    }
  }

  return (
    <header className="nw-topnav">
      <a href={Routes.home} className="nw-wordmark nw-display" lang="en">
        NAWA
      </a>
      <div className="nw-topnav-end">
        <LocaleSwitcher />
        {isSignedIn && user ? (
          <>
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
            <a href={Routes.signup} className="nw-btn nw-btn-primary">
              {t("actions.apply")}
            </a>
          </>
        )}
      </div>
    </header>
  );
}
