import IntakeWrapper from "@/libs/IntakeWrapper";
import { renderWithLocale } from "@/test/test-utils";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/hooks/Auth", () => ({
  usePermissions: () => ({ has: () => true, isLoading: false, isSignedIn: true }),
}));
vi.mock("next/navigation", () => ({ usePathname: () => "/intake" }));

const cycles = vi.hoisted(() => [
  {
    id: "cycle-1",
    program_id: "p1",
    program_name_ar: null,
    program_name_en: "Innovation Fellowship",
    name_ar: null,
    name_en: "Season 18",
    status: "active",
    opens_at: null,
    closes_at: null,
  },
]);

vi.mock("@/hooks/Intake", () => ({
  useCycles: () => ({ cycles, error: undefined, isLoading: false, refresh: vi.fn() }),
  useUpload: () => ({ run: vi.fn(), isPending: false, error: undefined }),
  useTriggerScore: () => ({ run: vi.fn(), isPending: false, error: undefined }),
  useUploadProgress: () => ({ total: 0, done: 0, failed: 0, stoppedReason: null }),
  useScoreProgress: () => ({ total: 0, done: 0, failed: 0, stoppedReason: null }),
}));

describe("IntakeWrapper column mapping", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders every target option's localized label after selecting a CSV (regression: snake_case vs camelCase i18n keys)", async () => {
    renderWithLocale(<IntakeWrapper />, "en");

    const csv = "name,email,idea\nA,a@x.io,idea text\n";
    const file = new File([csv], "batch.csv", { type: "text/csv" });
    // jsdom's File/Blob doesn't implement `.text()` — polyfill this instance
    // (a real browser File does).
    file.text = () => Promise.resolve(csv);
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    await userEvent.upload(fileInput, file);

    await waitFor(() => {
      expect(screen.getByText("Map columns")).toBeInTheDocument();
    });

    // Every <select> in the mapping rows must resolve every option's i18n
    // key without throwing (the bug: `applicant_name`/`applicant_email`
    // targets looked up `upload.columnMap.applicant_name`, which doesn't
    // exist — the real key is camelCase `applicantName`).
    for (const label of [
      "Applicant name",
      "Applicant email",
      "Phone",
      "Country",
      "Question key",
      "Not mapped (kept as extra data)",
    ]) {
      expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    }
  });
});
