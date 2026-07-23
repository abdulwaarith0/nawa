import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { renderWithLocale } from "../test-utils";
import { AiAttribution } from "./AiAttribution";

describe("AiAttribution", () => {
  it("renders the sparkle glyph AND the localized AI label under ar", () => {
    renderWithLocale(<AiAttribution>output</AiAttribution>, "ar");
    expect(screen.getByText("مُولّد بالذكاء الاصطناعي")).toBeInTheDocument();
    expect(screen.getByText("✦")).toBeInTheDocument();
    expect(screen.getByText("output")).toBeInTheDocument();
  });

  it("renders the English label under en", () => {
    renderWithLocale(<AiAttribution>output</AiAttribution>, "en");
    expect(screen.getByText("AI-generated")).toBeInTheDocument();
  });

  it("the sparkle is aria-hidden so the label carries the accessible name", () => {
    renderWithLocale(<AiAttribution>x</AiAttribution>, "en");
    expect(screen.getByText("✦")).toHaveAttribute("aria-hidden", "true");
  });

  it("shows a 'How was this produced?' disclosure when `how` is given", async () => {
    renderWithLocale(<AiAttribution how={<p>model details</p>}>x</AiAttribution>, "en");
    const summary = screen.getByText("How was this produced?");
    expect(summary).toBeInTheDocument();
    await userEvent.click(summary);
    expect(screen.getByText("model details")).toBeVisible();
  });

  it("omits the disclosure when `how` is absent", () => {
    renderWithLocale(<AiAttribution>x</AiAttribution>, "en");
    expect(screen.queryByText("How was this produced?")).not.toBeInTheDocument();
  });
});
