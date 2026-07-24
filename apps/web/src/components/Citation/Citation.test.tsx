import Citation from "@/components/Citation";
import { renderWithLocale } from "@/test/test-utils";
import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

describe("Citation", () => {
  it("highlights the exact quote in situ inside the source text", () => {
    renderWithLocale(
      <Citation
        text="We plan to build a solar irrigation kit for farmers."
        quote="solar irrigation kit"
      />,
      "en",
    );
    const mark = screen.getByTitle("AI-generated");
    expect(mark).toHaveTextContent("solar irrigation kit");
    expect(screen.getByText(/We plan to build a/)).toBeInTheDocument();
    expect(screen.getByText(/for farmers\./)).toBeInTheDocument();
  });

  it("tolerates whitespace differences between the quote and the source", () => {
    renderWithLocale(
      <Citation text={"Line one\nLine   two continues"} quote="Line one Line two" />,
      "en",
    );
    expect(screen.getByTitle("AI-generated").textContent).toMatch(/Line one\s+Line\s+two/);
  });

  it("falls back to plain text when the quote cannot be located", () => {
    renderWithLocale(
      <Citation text="Some unrelated answer text." quote="not present anywhere" />,
      "en",
    );
    expect(screen.queryByTitle("AI-generated")).not.toBeInTheDocument();
    expect(screen.getByText("Some unrelated answer text.")).toBeInTheDocument();
  });

  it("falls back to plain text for a blank quote", () => {
    renderWithLocale(<Citation text="Some text." quote="   " />, "en");
    expect(screen.queryByTitle("AI-generated")).not.toBeInTheDocument();
    expect(screen.getByText("Some text.")).toBeInTheDocument();
  });

  it("passes the lang prop through to the bidi wrapper", () => {
    const { container } = renderWithLocale(
      <Citation text="نص عربي" quote="عربي" lang="ar" />,
      "ar",
    );
    expect(container.querySelector("bdi")).toHaveAttribute("lang", "ar");
  });
});
