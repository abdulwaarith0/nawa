"use client";

import { Card } from "@/components";
import LocaleSwitcher from "@/layouts/LocaleSwitcher";
import { Routes } from "@nawa/contracts";
import { type ReactNode, useMemo } from "react";
import "./styles.css";

export interface IProps {
  children: ReactNode;
}

// Minimal centered-card shell for the auth pages (design-system §7): logo only
// + locale switcher, no nav.
export default function AuthShell({ children }: IProps) {
  return useMemo(
    () => (
      <div className="nw-auth-shell">
        <header className="nw-auth-header">
          <a href={Routes.home} className="nw-wordmark nw-display" lang="en">
            NAWA
          </a>
          <LocaleSwitcher />
        </header>
        <main className="nw-auth-main">
          <Card className="nw-auth-card">{children}</Card>
        </main>
      </div>
    ),
    [children],
  );
}
