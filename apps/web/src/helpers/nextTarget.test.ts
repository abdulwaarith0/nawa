import { afterEach, describe, expect, it, vi } from "vitest";
import { nextTarget } from "./nextTarget";

describe("nextTarget", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("falls back to homeForPermissions when no ?next is present and no perms are held", () => {
    vi.stubGlobal("location", { search: "" });
    expect(nextTarget()).toBe("/onboarding");
  });

  it("falls back to the permission-based home when perms are held", () => {
    vi.stubGlobal("location", { search: "" });
    expect(nextTarget(["nawa:console:intake"])).toBe("/intake");
  });

  it("returns a same-origin ?next target over the permission-based home", () => {
    vi.stubGlobal("location", { search: "?next=%2Fintake" });
    expect(nextTarget(["nawa:console:admin"])).toBe("/intake");
  });

  it("falls back to homeForPermissions for a non-relative ?next (open-redirect guard)", () => {
    vi.stubGlobal("location", { search: "?next=https%3A%2F%2Fevil.example.com" });
    expect(nextTarget(["nawa:console:journey"])).toBe("/journey");
  });
});
