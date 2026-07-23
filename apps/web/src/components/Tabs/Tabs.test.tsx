import { Tabs } from "@/components";
import { renderWithLocale } from "@/test/test-utils";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

const items = [
  { id: "dir", label: "Directory", content: <p>directory body</p> },
  { id: "req", label: "Requests", content: <p>requests body</p> },
  { id: "opp", label: "Opportunities", content: <p>opps body</p> },
];

describe("Tabs", () => {
  it("renders a tablist and shows the first panel by default", () => {
    renderWithLocale(<Tabs items={items} />, "en");
    expect(screen.getByRole("tablist")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Directory" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("directory body")).toBeVisible();
  });

  it("switches panel on click", async () => {
    renderWithLocale(<Tabs items={items} />, "en");
    await userEvent.click(screen.getByRole("tab", { name: "Requests" }));
    expect(screen.getByRole("tab", { name: "Requests" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("requests body")).toBeVisible();
  });

  it("ArrowRight moves to the next tab under LTR (en)", async () => {
    renderWithLocale(<Tabs items={items} />, "en");
    const first = screen.getByRole("tab", { name: "Directory" });
    first.focus();
    await userEvent.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "Requests" })).toHaveAttribute("aria-selected", "true");
  });

  it("ArrowRight moves to the PREVIOUS tab under RTL (ar), wrapping around", async () => {
    renderWithLocale(<Tabs items={items} />, "ar");
    const first = screen.getByRole("tab", { name: "Directory" });
    first.focus();
    // RTL: ArrowRight = visually-right = previous; from index 0 it wraps to last.
    await userEvent.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "Opportunities" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("ArrowLeft moves to the previous tab under LTR, wrapping to the last", async () => {
    renderWithLocale(<Tabs items={items} />, "en");
    screen.getByRole("tab", { name: "Directory" }).focus();
    await userEvent.keyboard("{ArrowLeft}");
    expect(screen.getByRole("tab", { name: "Opportunities" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("ArrowLeft moves to the next tab under RTL (ar)", async () => {
    renderWithLocale(<Tabs items={items} />, "ar");
    screen.getByRole("tab", { name: "Directory" }).focus();
    await userEvent.keyboard("{ArrowLeft}");
    expect(screen.getByRole("tab", { name: "Requests" })).toHaveAttribute("aria-selected", "true");
  });

  it("Home and End jump to the first and last tab", async () => {
    renderWithLocale(<Tabs items={items} />, "en");
    screen.getByRole("tab", { name: "Directory" }).focus();
    await userEvent.keyboard("{End}");
    expect(screen.getByRole("tab", { name: "Opportunities" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    await userEvent.keyboard("{Home}");
    expect(screen.getByRole("tab", { name: "Directory" })).toHaveAttribute("aria-selected", "true");
  });

  it("roving tabindex: only the active tab is tabbable", () => {
    renderWithLocale(<Tabs items={items} />, "en");
    expect(screen.getByRole("tab", { name: "Directory" })).toHaveAttribute("tabindex", "0");
    expect(screen.getByRole("tab", { name: "Requests" })).toHaveAttribute("tabindex", "-1");
  });
});
