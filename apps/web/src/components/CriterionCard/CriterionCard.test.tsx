import CriterionCard from "@/components/CriterionCard";
import { renderWithLocale } from "@/test/test-utils";
import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

describe("CriterionCard", () => {
  it("shows the English rationale under the en locale", () => {
    renderWithLocale(
      <CriterionCard
        criterionKey="regional_impact"
        score={8}
        weight={0.2}
        rationaleAr="سبب"
        rationaleEn="Strong regional fit."
        citations={[{ source: "answer:idea", quote: "solar kit" }]}
        originalAnswers={{ idea: "Our solar kit helps farmers." }}
      />,
      "en",
    );
    expect(screen.getByText("Strong regional fit.")).toBeInTheDocument();
    expect(screen.getByText("8")).toBeInTheDocument();
    expect(screen.getByText(/regional impact/i)).toBeInTheDocument();
    expect(screen.getByTitle("AI-generated")).toHaveTextContent("solar kit");
  });

  it("shows the Arabic rationale under the ar locale", () => {
    renderWithLocale(
      <CriterionCard
        criterionKey="novelty"
        score={7}
        weight={0.3}
        rationaleAr="فكرة مبتكرة."
        rationaleEn="A novel idea."
        citations={[]}
        originalAnswers={{}}
      />,
      "ar",
    );
    expect(screen.getByText("فكرة مبتكرة.")).toBeInTheDocument();
    expect(screen.queryByText("A novel idea.")).not.toBeInTheDocument();
  });

  it("falls back to a plain quote when the citation source can't be resolved", () => {
    renderWithLocale(
      <CriterionCard
        criterionKey="feasibility"
        score={6}
        weight={0.25}
        rationaleAr="سبب"
        rationaleEn="Feasible."
        citations={[{ source: "document:missing", quote: "some quote" }]}
        originalAnswers={{}}
      />,
      "en",
    );
    expect(screen.getByText("“some quote”")).toBeInTheDocument();
    expect(screen.queryByTitle("AI-generated")).not.toBeInTheDocument();
  });
});
