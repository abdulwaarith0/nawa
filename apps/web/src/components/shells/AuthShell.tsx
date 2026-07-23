import { Routes } from "@nawa/contracts";
import { LocaleSwitcher } from "./LocaleSwitcher";

// Minimal centered-card shell for the auth pages (design-system §7): logo only
// + locale switcher, no nav.
export function AuthShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="nw-auth-shell">
      <header className="nw-auth-header">
        <a href={Routes.home} className="nw-wordmark nw-display" lang="en">
          NAWA
        </a>
        <LocaleSwitcher />
      </header>
      <main className="nw-auth-main">
        <div className="nw-auth-card nw-card">{children}</div>
      </main>
    </div>
  );
}
