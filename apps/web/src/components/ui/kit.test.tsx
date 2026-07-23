import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { renderWithLocale } from "../test-utils";
import { Alert } from "./Alert";
import { Avatar } from "./Avatar";
import { Callout } from "./Callout";
import { Chip } from "./Chip";
import { Input } from "./Input";
import { Progress } from "./Progress";
import { StatTile } from "./StatTile";
import { EmptyState, ErrorState, Loading, Skeleton } from "./states";

describe("Input", () => {
  it("associates label, and links an error message via aria-describedby", () => {
    render(<Input label="Email" error="Required field" defaultValue="" />);
    const input = screen.getByLabelText("Email");
    expect(input).toHaveAttribute("aria-invalid", "true");
    const errorId = input.getAttribute("aria-describedby");
    expect(errorId).toBeTruthy();
    expect(screen.getByRole("alert")).toHaveTextContent("Required field");
  });

  it("links a hint (not an error) when there is no error", () => {
    render(<Input label="Handle" hint="lowercase only" />);
    const input = screen.getByLabelText("Handle");
    expect(input).not.toHaveAttribute("aria-invalid");
    expect(input.getAttribute("aria-describedby")).toBeTruthy();
    expect(screen.getByText("lowercase only")).toBeInTheDocument();
  });

  it("opts into dir=auto for free-text", () => {
    render(<Input label="Bio" dirAuto />);
    expect(screen.getByLabelText("Bio")).toHaveAttribute("dir", "auto");
  });

  it("renders a bare input (no label/hint/error) with an explicit id and no describedby/dir", () => {
    render(<Input id="bare" aria-label="bare" />);
    const input = screen.getByLabelText("bare");
    expect(input).toHaveAttribute("id", "bare");
    expect(input).not.toHaveAttribute("aria-describedby");
    expect(input).not.toHaveAttribute("dir");
  });
});

describe("Alert", () => {
  it("danger uses role=alert and carries an icon + text (not colour alone)", () => {
    renderWithLocale(<Alert severity="danger">Boom</Alert>, "en");
    const alert = screen.getByRole("alert");
    expect(alert).toHaveAttribute("data-severity", "danger");
    expect(alert.querySelector(".nw-alert-icon")).toBeInTheDocument();
    expect(alert).toHaveTextContent("Boom");
  });

  it("info uses role=status and can be dismissed with a localized label", async () => {
    const onDismiss = vi.fn();
    renderWithLocale(
      <Alert severity="info" onDismiss={onDismiss}>
        FYI
      </Alert>,
      "ar",
    );
    const btn = screen.getByRole("button", { name: "إغلاق" });
    await userEvent.click(btn);
    expect(onDismiss).toHaveBeenCalledOnce();
  });
});

describe("Callout", () => {
  it("renders a note with a tone", () => {
    render(<Callout tone="success">All good</Callout>);
    const note = screen.getByRole("note");
    expect(note).toHaveAttribute("data-tone", "success");
  });
});

describe("Chip", () => {
  it("selectable chip toggles aria-pressed and fires onSelect", async () => {
    const onSelect = vi.fn();
    render(
      <Chip selected onSelect={onSelect}>
        robotics
      </Chip>,
    );
    const btn = screen.getByRole("button", { name: "robotics" });
    expect(btn).toHaveAttribute("aria-pressed", "true");
    await userEvent.click(btn);
    expect(onSelect).toHaveBeenCalledOnce();
  });

  it("removable chip has a labeled remove button (localized) and flips in RTL", async () => {
    const onRemove = vi.fn();
    renderWithLocale(<Chip onRemove={onRemove}>health-tech</Chip>, "en");
    const remove = screen.getByRole("button", { name: "Close" });
    expect(remove).toHaveClass("nw-icon-dir");
    await userEvent.click(remove);
    expect(onRemove).toHaveBeenCalledOnce();
  });

  it("disabled chip reports data-state=disabled", () => {
    render(
      <Chip disabled onSelect={() => {}}>
        x
      </Chip>,
    );
    expect(screen.getByText("x").closest(".nw-chip")).toHaveAttribute("data-state", "disabled");
  });
});

describe("state components", () => {
  it("EmptyState renders headline + constructive action", () => {
    render(
      <EmptyState headline="No applications yet" action={<button type="button">Upload</button>} />,
    );
    expect(screen.getByText("No applications yet")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Upload" })).toBeInTheDocument();
  });

  it("EmptyState renders an icon and description when given", () => {
    render(
      <EmptyState
        headline="Empty"
        description="nothing to show"
        icon={<span data-testid="empty-icon" />}
      />,
    );
    expect(screen.getByTestId("empty-icon")).toBeInTheDocument();
    expect(screen.getByText("nothing to show")).toBeInTheDocument();
  });

  it("Skeleton is a busy status region", () => {
    render(<Skeleton ariaLabel="loading row" />);
    const sk = screen.getByRole("status");
    expect(sk).toHaveAttribute("aria-busy", "true");
  });

  it("ErrorState shows the localized default message + retry", async () => {
    const onRetry = vi.fn();
    renderWithLocale(<ErrorState onRetry={onRetry} />, "ar");
    expect(screen.getByRole("alert")).toHaveTextContent("حدث خطأ ما");
    await userEvent.click(screen.getByRole("button", { name: "إعادة المحاولة" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("ErrorState shows an explicit message and omits retry when no handler", () => {
    renderWithLocale(<ErrorState message="Custom failure" />, "en");
    expect(screen.getByRole("alert")).toHaveTextContent("Custom failure");
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("Loading announces the localized loading string", () => {
    renderWithLocale(<Loading />, "en");
    expect(screen.getAllByText("Loading…").length).toBeGreaterThan(0);
  });
});

describe("Progress", () => {
  it("is a progressbar with the right ARIA values", () => {
    render(<Progress value={30} max={60} valueText="step 1 of 2" label="Onboarding" />);
    const bar = screen.getByRole("progressbar", { name: "Onboarding" });
    expect(bar).toHaveAttribute("aria-valuenow", "30");
    expect(bar).toHaveAttribute("aria-valuemax", "60");
    expect(bar).toHaveAttribute("aria-valuetext", "step 1 of 2");
  });
});

describe("StatTile", () => {
  it("renders the value with Latin digits and a positive delta tone", () => {
    renderWithLocale(<StatTile label="MRR" value={1200} unit="QAR" deltaPct={20} />, "ar");
    expect(screen.getByText("MRR")).toBeInTheDocument();
    // Latin digits even under ar
    const value = screen.getByText(/1[,٬]?200/);
    expect(value).toBeInTheDocument();
    const delta = screen.getByText(/▲/);
    expect(delta).toHaveAttribute("data-tone", "up");
  });

  it("renders a down tone for a negative delta", () => {
    renderWithLocale(<StatTile label="Churn" value={5} deltaPct={-3} />, "en");
    expect(screen.getByText(/▼/)).toHaveAttribute("data-tone", "down");
  });

  it("omits the delta entirely when deltaPct is null", () => {
    renderWithLocale(<StatTile label="Team" value={4} deltaPct={null} />, "en");
    expect(screen.queryByText(/▲|▼/)).not.toBeInTheDocument();
  });
});

describe("Avatar", () => {
  it("shows initials when there is no image and labels itself", () => {
    render(<Avatar name="Ahmed Al-Sayed" />);
    const img = screen.getByRole("img", { name: "Ahmed Al-Sayed" });
    expect(img).toHaveTextContent("AA");
  });

  it("renders an <img> with alt when src is provided", () => {
    render(<Avatar name="Sara" src="https://example.com/a.png" />);
    const img = screen.getByRole("img", { name: "Sara" });
    expect(img.tagName.toLowerCase()).toBe("img");
    expect(img).toHaveAttribute("src", "https://example.com/a.png");
  });
});
