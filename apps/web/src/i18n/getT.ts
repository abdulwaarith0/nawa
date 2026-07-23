import type { TLocale } from "@nawa/contracts";

import { type Namespace, getDictionary } from "./dictionaries";
import { type TFunction, createLookup } from "./lookup";

// Server-component translator equivalent of useT.
export function getT(locale: TLocale, namespace: Namespace): TFunction {
  return createLookup(locale, getDictionary(locale, namespace) as Record<string, never>);
}
