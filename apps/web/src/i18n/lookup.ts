// The shared translation-lookup engine: dot-namespaced keys, {name}
// interpolation, and CLDR pluralization (Arabic needs zero/two/few/many).

import type { TLocale } from "@nawa/contracts";

export type TParams = Record<string, string | number>;
export type TFunction = (key: string, params?: TParams) => string;

// Missing keys throw in development (loud, greppable) and render the key in
// production — never a silent English fallback.
const THROW_ON_MISSING = process.env.NODE_ENV !== "production";

type DictNode = string | { [k: string]: DictNode };

function resolvePath(dict: Record<string, DictNode>, key: string): DictNode | undefined {
  let node: DictNode | undefined = dict;
  for (const part of key.split(".")) {
    if (node === undefined || typeof node === "string") return undefined;
    node = node[part];
  }
  return node;
}

function interpolate(template: string, params?: TParams): string {
  if (!params) return template;
  return template.replace(/\{(\w+)\}/g, (_m, name: string) =>
    name in params ? String(params[name]) : `{${name}}`,
  );
}

export function createLookup(
  locale: TLocale,
  dict: Record<string, DictNode>,
  throwOnMissing = THROW_ON_MISSING,
): TFunction {
  const plural = new Intl.PluralRules(locale === "ar" ? "ar" : "en");
  return (key, params) => {
    let value = resolvePath(dict, key);

    // Pluralization: when the node is an object and a numeric `count` is given,
    // pick the CLDR category (falling back to `other`).
    if (value && typeof value === "object" && params && typeof params.count === "number") {
      const category = plural.select(params.count);
      value = value[category] ?? value.other;
    }

    if (typeof value !== "string") {
      if (throwOnMissing) throw new Error(`Missing i18n key: ${key}`);
      return key;
    }
    return interpolate(value, params);
  };
}
