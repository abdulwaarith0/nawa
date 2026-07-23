import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { renderWithLocale } from "../test-utils";
import { AuthShell } from "./AuthShell";

describe("AuthShell", () => {
  it("renders the wordmark, a locale switcher, and its children", () => {
    // Rendered under ar, so the switcher offers English.
    renderWithLocale(
      <AuthShell>
        <p>child content</p>
      </AuthShell>,
      "ar",
    );
    expect(screen.getByText("NAWA")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Switch to English" })).toBeInTheDocument();
    expect(screen.getByText("child content")).toBeInTheDocument();
  });
});
