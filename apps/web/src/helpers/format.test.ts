import { describe, expect, it } from "vitest";
import { formatCurrency, formatDate, formatNumber, formatPercent } from "./format";

const EASTERN_ARABIC = /[٠-٩]/; // ٠-٩

describe("numeral policy", () => {
  it("formatNumber uses ASCII digits under ar (never Eastern Arabic)", () => {
    const out = formatNumber(1234.5, "ar");
    expect(out).not.toMatch(EASTERN_ARABIC);
    expect(out).toMatch(/[0-9]/);
  });

  it("formatNumber uses ASCII digits under en", () => {
    expect(formatNumber(1234, "en")).toMatch(/1,?234/);
  });

  it("formatCurrency renders Latin digits in both locales", () => {
    expect(formatCurrency(1200, "ar")).not.toMatch(EASTERN_ARABIC);
    expect(formatCurrency(1200, "en")).not.toMatch(EASTERN_ARABIC);
  });

  it("formatPercent renders a percent with Latin digits", () => {
    const out = formatPercent(0.12, "ar");
    expect(out).toContain("%");
    expect(out).not.toMatch(EASTERN_ARABIC);
  });

  it("formatDate under ar uses Arabic month names but Latin digits", () => {
    const out = formatDate("2026-03-15", "ar");
    expect(out).not.toMatch(EASTERN_ARABIC); // digits are Latin
    // contains a non-ASCII (Arabic) letter for the month name
    expect(out).toMatch(/[؀-ۿ]/);
  });

  it("formatDate accepts a Date object", () => {
    const out = formatDate(new Date("2026-03-15"), "en");
    expect(out).toMatch(/2026/);
  });
});
