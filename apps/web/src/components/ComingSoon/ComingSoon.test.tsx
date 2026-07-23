import { ComingSoon } from "@/components";
import { renderWithLocale } from "@/test/test-utils";
import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

describe("ComingSoon", () => {
  it("renders the localized not-available state under en", () => {
    renderWithLocale(<ComingSoon />, "en");
    expect(screen.getByText("Not available yet")).toBeInTheDocument();
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("renders the Arabic not-available state", () => {
    renderWithLocale(<ComingSoon />, "ar");
    expect(screen.getByText("غير متاح بعد")).toBeInTheDocument();
  });
});
