import DecisionPanel from "@/components/DecisionPanel";
import { renderWithLocale } from "@/test/test-utils";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

const COHORTS = [
  { id: "cohort-1", label: "Season 18 · Cohort A" },
  { id: "cohort-2", label: "Season 18 · Cohort B" },
];

describe("DecisionPanel", () => {
  it("submits immediately when the decision matches the AI band (no reason required)", async () => {
    const onSubmit = vi.fn();
    renderWithLocale(<DecisionPanel aiBand="shortlist" onSubmit={onSubmit} />, "en");

    await userEvent.click(screen.getByRole("button", { name: "Shortlist" }));
    expect(screen.queryByText(/overriding the AI ranking/)).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Submit decision" }));

    expect(onSubmit).toHaveBeenCalledWith({
      decision: "shortlist",
      reason: undefined,
      cohortId: undefined,
    });
  });

  it("requires a reason when the decision diverges from the AI band", async () => {
    const onSubmit = vi.fn();
    renderWithLocale(<DecisionPanel aiBand="shortlist" onSubmit={onSubmit} />, "en");

    await userEvent.click(screen.getByRole("button", { name: "Reject" }));
    expect(screen.getByText(/overriding the AI ranking/)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Submit decision" }));
    expect(onSubmit).not.toHaveBeenCalled();
    expect(
      screen.getAllByText(
        "You are overriding the AI ranking — a reason is required and will be logged.",
      ).length,
    ).toBeGreaterThan(0);

    await userEvent.type(screen.getByLabelText("Reason"), "Weak team fit");
    await userEvent.click(screen.getByRole("button", { name: "Submit decision" }));
    expect(onSubmit).toHaveBeenCalledWith({
      decision: "reject",
      reason: "Weak team fit",
      cohortId: undefined,
    });
  });

  it("treats accept as matching (not overriding) a shortlist band, and picks a real cohort", async () => {
    const onSubmit = vi.fn();
    renderWithLocale(
      <DecisionPanel aiBand="shortlist" cohorts={COHORTS} onSubmit={onSubmit} />,
      "en",
    );

    await userEvent.click(screen.getByRole("button", { name: "Accept into cohort" }));
    expect(screen.queryByText(/overriding the AI ranking/)).not.toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("Cohort"), "cohort-2");
    await userEvent.click(screen.getByRole("button", { name: "Submit decision" }));

    expect(onSubmit).toHaveBeenCalledWith({
      decision: "accept",
      reason: undefined,
      cohortId: "cohort-2",
    });
  });

  it("requires a cohort to be picked before accept can submit", async () => {
    const onSubmit = vi.fn();
    renderWithLocale(
      <DecisionPanel aiBand="shortlist" cohorts={COHORTS} onSubmit={onSubmit} />,
      "en",
    );

    await userEvent.click(screen.getByRole("button", { name: "Accept into cohort" }));
    await userEvent.click(screen.getByRole("button", { name: "Submit decision" }));

    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByText("A cohort is required to accept into.")).toBeInTheDocument();
  });

  it("shows an honest message instead of a picker when the cycle has no cohorts yet", async () => {
    const onSubmit = vi.fn();
    renderWithLocale(<DecisionPanel aiBand="shortlist" cohorts={[]} onSubmit={onSubmit} />, "en");

    await userEvent.click(screen.getByRole("button", { name: "Accept into cohort" }));
    expect(
      screen.getByText(
        "No cohorts exist yet for this cycle — create one before accepting applicants.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText("Cohort")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Submit decision" }));
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("disables submit until a decision is chosen", () => {
    renderWithLocale(<DecisionPanel aiBand="waitlist" onSubmit={vi.fn()} />, "en");
    expect(screen.getByRole("button", { name: "Submit decision" })).toBeDisabled();
  });
});
