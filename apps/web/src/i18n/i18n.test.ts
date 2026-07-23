import { describe, expect, it } from "vitest";
import { DICTIONARIES, getDictionary } from "./dictionaries";
import { getT } from "./getT";
import { createLookup } from "./lookup";

const CLDR_CATEGORIES = new Set(["zero", "one", "two", "few", "many", "other"]);

function isPluralNode(obj: Record<string, unknown>): boolean {
  const keys = Object.keys(obj);
  return keys.length > 0 && keys.every((k) => CLDR_CATEGORIES.has(k));
}

function collectKeys(obj: unknown, prefix = ""): string[] {
  if (obj === null || typeof obj !== "object") return [prefix];
  // A plural node's CLDR categories legitimately differ by language, so treat
  // it as a single leaf for parity purposes.
  if (isPluralNode(obj as Record<string, unknown>)) return [prefix];
  return Object.entries(obj as Record<string, unknown>).flatMap(([k, v]) =>
    collectKeys(v, prefix ? `${prefix}.${k}` : k),
  );
}

describe("i18n lookup", () => {
  it("resolves a dot-namespaced key", () => {
    const t = getT("en", "common");
    expect(t("actions.save")).toBe("Save");
    expect(t("states.loading")).toBe("Loading…");
  });

  it("resolves the Arabic value under ar", () => {
    const t = getT("ar", "common");
    expect(t("actions.save")).toBe("حفظ");
  });

  it("interpolates {params}", () => {
    const dict = { greeting: "Hello {name}" };
    const t = createLookup("en", dict, true);
    expect(t("greeting", { name: "Alice" })).toBe("Hello Alice");
  });

  it("pluralizes with .one/.other under en", () => {
    const t = getT("en", "common");
    expect(t("results.count", { count: 1 })).toBe("1 result");
    expect(t("results.count", { count: 5 })).toBe("5 results");
  });

  it("pluralizes with Arabic CLDR categories", () => {
    const t = getT("ar", "common");
    // Arabic 'zero' category for 0
    expect(t("results.count", { count: 0 })).toBe("لا نتائج");
    // 'one' for 1, 'two' for 2
    expect(t("results.count", { count: 1 })).toBe("نتيجة واحدة");
    expect(t("results.count", { count: 2 })).toBe("نتيجتان");
  });

  it("leaves an unknown {param} placeholder intact", () => {
    const t = createLookup("en", { greeting: "Hi {name}" }, true);
    expect(t("greeting", { other: "x" })).toBe("Hi {name}");
  });

  it("returns the template unchanged when no params are given", () => {
    const t = createLookup("en", { plain: "no params here" }, true);
    expect(t("plain")).toBe("no params here");
  });

  it("falls back to the `other` plural form for an uncategorized count", () => {
    // en only defines one/other; count=2 selects 'other'.
    const t = createLookup("en", { n: { one: "{count} item", other: "{count} items" } }, true);
    expect(t("n", { count: 2 })).toBe("2 items");
  });

  it("returns the key when a plural node lacks the needed category and has no other", () => {
    const t = createLookup("en", { n: { one: "one" } }, false);
    // count=5 -> 'other' which is missing -> not a string -> key returned
    expect(t("n", { count: 5 })).toBe("n");
  });

  it("throws on a missing key in development mode", () => {
    const t = createLookup("en", { a: "b" }, true);
    expect(() => t("does.not.exist")).toThrow(/Missing i18n key/);
  });

  it("renders the key (no throw) when throwOnMissing is false", () => {
    const t = createLookup("en", { a: "b" }, false);
    expect(t("does.not.exist")).toBe("does.not.exist");
  });
});

describe("i18n key parity", () => {
  it("ar and en have identical key sets for every namespace", () => {
    for (const namespace of ["common", "ai"] as const) {
      const enKeys = collectKeys(getDictionary("en", namespace)).sort();
      const arKeys = collectKeys(getDictionary("ar", namespace)).sort();
      expect(arKeys, `namespace ${namespace}`).toEqual(enKeys);
    }
  });

  it("every locale exposes the same namespaces", () => {
    expect(Object.keys(DICTIONARIES.ar).sort()).toEqual(Object.keys(DICTIONARIES.en).sort());
  });
});
