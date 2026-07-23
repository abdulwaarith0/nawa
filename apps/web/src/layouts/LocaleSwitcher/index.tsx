"use client";

import { useLocale } from "@/i18n/LocaleProvider";
import { useCallback, useMemo } from "react";

// Sets the nw_locale cookie and re-renders with the new dir. Lives in the top
// navigation on every shell (design-system §5.2). Extracted `setLocaleCookie`
// so the cookie logic is unit-testable without a full page reload.
export function setLocaleCookie(next: "ar" | "en"): void {
  document.cookie = `nw_locale=${next}; path=/; max-age=${60 * 60 * 24 * 365}; samesite=lax`;
}

export default function LocaleSwitcher() {
  const locale = useLocale();
  const next = locale === "ar" ? "en" : "ar";

  const onClick = useCallback(() => {
    setLocaleCookie(next);
    // A full reload re-runs the server layout so <html dir> flips too.
    window.location.reload();
  }, [next]);

  return useMemo(
    () => (
      <button
        type="button"
        className="nw-btn nw-btn-ghost"
        onClick={onClick}
        aria-label={next === "en" ? "Switch to English" : "التبديل إلى العربية"}
      >
        {next === "en" ? "EN" : "ع"}
      </button>
    ),
    [next, onClick],
  );
}
