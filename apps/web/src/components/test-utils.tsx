import type { TLocale } from "@nawa/contracts";
import { type RenderResult, render } from "@testing-library/react";
import { LocaleProvider } from "../i18n/LocaleProvider";

// Render a component inside a locale context (defaults to Arabic, the app default).
export function renderWithLocale(ui: React.ReactElement, locale: TLocale = "ar"): RenderResult {
  return render(<LocaleProvider locale={locale}>{ui}</LocaleProvider>);
}
