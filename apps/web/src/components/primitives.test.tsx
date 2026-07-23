import { Badge, Bidi, Card } from "@/components";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

describe("Bidi", () => {
  it("wraps user content in a <bdi> with dir=auto by default", () => {
    render(<Bidi>أحمد</Bidi>);
    const bdi = screen.getByText("أحمد");
    expect(bdi.tagName.toLowerCase()).toBe("bdi");
    expect(bdi).toHaveAttribute("dir", "auto");
  });

  it("passes an explicit dir and lang for verbatim foreign fragments", () => {
    render(
      <Bidi dir="ltr" lang="fr">
        Bonjour
      </Bidi>,
    );
    const bdi = screen.getByText("Bonjour");
    expect(bdi).toHaveAttribute("dir", "ltr");
    expect(bdi).toHaveAttribute("lang", "fr");
  });
});

describe("Card", () => {
  it("renders children with the .nw-card class and merges extra classes", () => {
    render(<Card className="extra">body</Card>);
    const card = screen.getByText("body");
    expect(card).toHaveClass("nw-card", "extra");
  });

  it("renders with just the base class when no className is given", () => {
    render(<Card>bare</Card>);
    const card = screen.getByText("bare");
    expect(card).toHaveClass("nw-card");
    expect(card.className.trim()).toBe("nw-card");
  });
});

describe("Badge", () => {
  it("renders with a semantic tone data attribute", () => {
    render(<Badge tone="success">Live</Badge>);
    const badge = screen.getByText("Live");
    expect(badge).toHaveClass("nw-badge");
    expect(badge).toHaveAttribute("data-tone", "success");
  });

  it("renders an icon alongside the label (not colour alone)", () => {
    render(
      <Badge tone="danger" icon={<span data-testid="icon" />}>
        Removed
      </Badge>,
    );
    expect(screen.getByTestId("icon")).toBeInTheDocument();
    expect(screen.getByText("Removed")).toBeInTheDocument();
  });
});
