import { LocaleProvider } from "@/i18n/LocaleProvider";
import type { TLocale } from "@nawa/contracts";
import { type RenderResult, render } from "@testing-library/react";
import type { ReactElement } from "react";

// Render a component inside a locale context (defaults to Arabic, the app default).
export function renderWithLocale(ui: ReactElement, locale: TLocale = "ar"): RenderResult {
  return render(<LocaleProvider locale={locale}>{ui}</LocaleProvider>);
}
