// Numeral policy (design-system §3.3): all quantitative data renders in Western
// Arabic (ASCII 0-9) digits in BOTH locales, so figures stay comparable across a
// bilingual screen and read identically to screen readers. Feature code never
// calls toLocaleString directly — it uses these helpers.

import type { TLocale } from "@nawa/contracts";

// Locales pinned to the Latin numbering system.
const NUMBER_LOCALE: Record<TLocale, string> = {
  ar: "ar-QA-u-nu-latn",
  en: "en-QA",
};

// Dates: Arabic month names under `ar`, but Latin digits (nu-latn).
const DATE_LOCALE: Record<TLocale, string> = {
  ar: "ar-QA-u-nu-latn",
  en: "en-QA",
};

export function formatNumber(
  value: number,
  locale: TLocale,
  options?: Intl.NumberFormatOptions,
): string {
  return new Intl.NumberFormat(NUMBER_LOCALE[locale], options).format(value);
}

export function formatCurrency(value: number, locale: TLocale, currency = "QAR"): string {
  return formatNumber(value, locale, {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  });
}

export function formatPercent(value: number, locale: TLocale, fractionDigits = 1): string {
  return formatNumber(value, locale, {
    style: "percent",
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  });
}

export function formatDate(
  value: Date | string,
  locale: TLocale,
  options: Intl.DateTimeFormatOptions = { year: "numeric", month: "long", day: "numeric" },
): string {
  const date = typeof value === "string" ? new Date(value) : value;
  return new Intl.DateTimeFormat(DATE_LOCALE[locale], options).format(date);
}
