import EligibilityProofPanel from "@/components/EligibilityProofPanel";
import { renderWithLocale } from "@/test/test-utils";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { run } = vi.hoisted(() => ({ run: vi.fn() }));

vi.mock("@/hooks/Intake", () => ({
  useRecordEligibilityProof: () => ({ run, isPending: false, error: null }),
}));

describe("EligibilityProofPanel", () => {
  beforeEach(() => {
    run.mockReset();
  });

  it("disables record until a contract address and tx id are entered", () => {
    renderWithLocale(<EligibilityProofPanel applicationId="app-1" />, "en");
    expect(screen.getByRole("button", { name: "Record proof" })).toBeDisabled();
  });

  it("sends the reference and verdict, then reports the recorded proof ref", async () => {
    run.mockResolvedValue({
      application_id: "app-1",
      proof_ref: "460870b0@005aa3a8",
      verdict: "eligible",
      network: "preview",
    });
    const onRecorded = vi.fn();
    renderWithLocale(<EligibilityProofPanel applicationId="app-1" onRecorded={onRecorded} />, "en");

    await userEvent.type(screen.getByLabelText("Contract address"), "460870b0");
    await userEvent.type(screen.getByLabelText("Proof transaction id"), "005aa3a8");
    await userEvent.selectOptions(screen.getByLabelText("Network"), "preview");
    await userEvent.click(screen.getByRole("button", { name: "Record proof" }));

    expect(run).toHaveBeenCalledWith({
      contractAddress: "460870b0",
      txId: "005aa3a8",
      verdict: "eligible",
      network: "preview",
      minAge: null,
      maxPriorFunding: null,
    });
    expect(onRecorded).toHaveBeenCalled();
    expect(screen.getByText(/460870b0@005aa3a8/)).toBeInTheDocument();
  });

  it("does not submit when the required fields are blank", async () => {
    renderWithLocale(<EligibilityProofPanel applicationId="app-1" />, "en");
    await userEvent.click(screen.getByRole("button", { name: "Record proof" }));
    expect(run).not.toHaveBeenCalled();
  });
});
