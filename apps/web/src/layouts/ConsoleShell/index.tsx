"use client";

import { usePermissions } from "@/hooks/Auth";
import { useT } from "@/i18n/useT";
import LocaleSwitcher from "@/layouts/LocaleSwitcher";
import { Routes } from "@nawa/contracts";
import { usePathname } from "next/navigation";
import { type ReactNode, useCallback, useMemo, useState } from "react";
import "./styles.css";

interface NavItem {
  key: string;
  href: string;
  gate: string;
}
interface NavSection {
  section: string;
  items: NavItem[];
}

const NAV: NavSection[] = [
  {
    section: "workspace",
    items: [
      { key: "intake", href: Routes.intake.home, gate: "nawa:console:intake" },
      { key: "journey", href: Routes.journey.home, gate: "nawa:console:journey" },
      { key: "portfolio", href: Routes.reports.portfolio, gate: "nawa:console:reports" },
      { key: "generate", href: Routes.reports.generate, gate: "nawa:reports:generate" },
    ],
  },
  {
    section: "administration",
    items: [
      { key: "overview", href: Routes.admin.home, gate: "nawa:console:admin" },
      { key: "groups", href: Routes.admin.iamGroups, gate: "nawa:iam:manage" },
      { key: "policies", href: Routes.admin.iamPolicies, gate: "nawa:iam:manage" },
      { key: "audit", href: Routes.admin.audit, gate: "nawa:audit:read" },
    ],
  },
];

export interface IProps {
  title: string;
  children: ReactNode;
}

// Console shell (design-system §7.2): fixed permission-gated sidebar at
// inset-inline-start, content area on sand-50 with a sticky page-title header.
// Sidebar sections render only the entries the session's permissions allow;
// the API re-checks authoritatively. Collapses to a drawer below 768px.
export default function ConsoleShell({ title, children }: IProps) {
  const t = useT("console");
  const pathname = usePathname();
  const { has } = usePermissions();
  const [open, setOpen] = useState(false);

  const sections = useMemo(
    () =>
      NAV.map((s) => ({ ...s, items: s.items.filter((i) => has(i.gate)) })).filter(
        (s) => s.items.length > 0,
      ),
    [has],
  );

  const closeDrawer = useCallback(() => setOpen(false), []);

  return (
    <div className="nw-console" data-open={open}>
      <button
        type="button"
        className="nw-console-scrim"
        aria-hidden={!open}
        tabIndex={-1}
        onClick={closeDrawer}
      />
      <aside className="nw-console-sidebar" aria-label={t("nav.menu")}>
        <a href={Routes.home} className="nw-wordmark nw-display nw-console-brand" lang="en">
          NAWA
        </a>
        <nav className="nw-console-nav">
          {sections.map((s) => (
            <div key={s.section} className="nw-console-section">
              <p className="nw-console-section-label">{t(`nav.sections.${s.section}`)}</p>
              {s.items.map((item) => {
                const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
                return (
                  <a
                    key={item.key}
                    href={item.href}
                    className="nw-console-link"
                    data-active={active}
                    aria-current={active ? "page" : undefined}
                    onClick={closeDrawer}
                  >
                    {t(`nav.${item.key}`)}
                  </a>
                );
              })}
            </div>
          ))}
        </nav>
      </aside>
      <div className="nw-console-body">
        <header className="nw-console-header">
          <button
            type="button"
            className="nw-btn nw-btn-ghost nw-console-menu"
            aria-label={open ? t("nav.close") : t("nav.menu")}
            aria-expanded={open}
            onClick={() => setOpen((v) => !v)}
          >
            ☰
          </button>
          <h1 className="nw-display nw-console-title">{title}</h1>
          <div className="nw-console-header-end">
            <LocaleSwitcher />
          </div>
        </header>
        <main className="nw-console-main">{children}</main>
      </div>
    </div>
  );
}
