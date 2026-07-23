"use client";

import { useLocale } from "./LocaleProvider";
import { type Namespace, getDictionary } from "./dictionaries";
import { type TFunction, createLookup } from "./lookup";

// Client-component translator: useT(namespace) -> t(key, params).
export function useT(namespace: Namespace): TFunction {
  const locale = useLocale();
  return createLookup(locale, getDictionary(locale, namespace) as Record<string, never>);
}
