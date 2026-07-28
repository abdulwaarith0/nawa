"use client";

import { Avatar } from "@/components";
import { usePermissions, useSession } from "@/hooks/Auth";
import { useT } from "@/i18n/useT";
import NotificationBell from "@/layouts/ConsoleShell/NotificationBell";
import QuickCreate from "@/layouts/ConsoleShell/QuickCreate";
import LocaleSwitcher from "@/layouts/LocaleSwitcher";
import { getApiClient } from "@/lib/apiClient";
import { Routes } from "@nawa/contracts";
import { usePathname } from "next/navigation";
import { type ReactNode, useCallback, useMemo, useState } from "react";
import "./styles.css";

interface NavItem {
  key: string;
  href: string;
  // null = no permission check, always shown (e.g. the dashboard/Home link).
  gate: string | null;
}

const NAV: NavItem[] = [
  { key: "dashboard", href: Routes.dashboard, gate: null },
  { key: "intake", href: Routes.intake.home, gate: "nawa:console:intake" },
  { key: "journey", href: Routes.journey.home, gate: "nawa:console:journey" },
  { key: "community", href: Routes.community.home, gate: "nawa:community:read" },
  { key: "reports", href: Routes.reports.portfolio, gate: "nawa:console:reports" },
  { key: "admin", href: Routes.admin.home, gate: "nawa:console:admin" },
];

export interface IProps {
  // Legacy: a bare title for pages not yet migrated to render their own rich
  // `.nw-page-head` (eyebrow + title + actions) — see DashboardWrapper for
  // the current pattern new pages should follow instead.
  title?: string;
  children: ReactNode;
}

// Console shell (ported from the approved new design): sticky top bar
// (brand, permission-gated flat nav, locale switcher, avatar/sign-out)
// replacing the old fixed sidebar. Nav items render only what the session's
// permissions allow; the API re-checks authoritatively.
export default function ConsoleShell({ title, children }: IProps) {
  const t = useT("console");
  const tCommon = useT("common");
  const pathname = usePathname();
  const { has } = usePermissions();
  const { user, isSignedIn } = useSession();
  const [navOpen, setNavOpen] = useState(false);

  const items = useMemo(() => NAV.filter((i) => i.gate === null || has(i.gate)), [has]);

  const closeNav = useCallback(() => setNavOpen(false), []);

  const onSignOut = useCallback(async () => {
    try {
      await getApiClient().auth.logout();
    } finally {
      window.location.assign(Routes.home);
    }
  }, []);

  return (
    <div className="nw-console" data-nav-open={navOpen}>
      <header className="nw-topbar">
        <div className="nw-topbar-inner">
          <a href={Routes.home} className="nw-console-brand" lang="en">
            <img className="nw-console-brand-mark" src="/brand/nawa-emblem.svg" alt="" />
            <span className="nw-console-brand-name">Nawa</span>
          </a>

          <button
            type="button"
            className="nw-btn nw-btn-ghost nw-console-menu"
            aria-label={navOpen ? t("nav.close") : t("nav.menu")}
            aria-expanded={navOpen}
            onClick={() => setNavOpen((v) => !v)}
          >
            ☰
          </button>

          <nav className="nw-primary-nav" aria-label={t("nav.menu")}>
            {items.map((item) => {
              const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
              return (
                <a
                  key={item.key}
                  href={item.href}
                  data-active={active}
                  aria-current={active ? "page" : undefined}
                  onClick={closeNav}
                >
                  {t(`nav.${item.key}`)}
                </a>
              );
            })}
          </nav>

          <div className="nw-topbar-actions">
            <LocaleSwitcher />
            {isSignedIn && user ? (
              <>
                <NotificationBell />
                <a
                  href={Routes.profile(user.username)}
                  className="nw-topbar-avatar-link"
                  aria-label={user.full_name}
                >
                  <Avatar name={user.full_name} size={38} />
                </a>
                <button type="button" className="nw-btn nw-btn-ghost" onClick={onSignOut}>
                  {tCommon("actions.signOut")}
                </button>
                <QuickCreate />
              </>
            ) : null}
          </div>
        </div>
      </header>

      <main className="nw-console-main">
        {title ? (
          <div className="nw-shell">
            <div className="nw-page-head">
              <h1 className="nw-page-title">{title}</h1>
            </div>
            {children}
          </div>
        ) : (
          children
        )}
      </main>
    </div>
  );
}
