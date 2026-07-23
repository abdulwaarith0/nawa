// Dictionary registry: locale + namespace -> plain JSON. Both locales must
// carry identical key sets (enforced by the i18n:check script + a unit test).

import type { TLocale } from "@nawa/contracts";

import arAi from "./ar/ai.json";
import arCommon from "./ar/common.json";
import enAi from "./en/ai.json";
import enCommon from "./en/common.json";

export type Namespace = "common" | "ai";

type Dict = Record<string, unknown>;

export const DICTIONARIES: Record<TLocale, Record<Namespace, Dict>> = {
  en: { common: enCommon, ai: enAi },
  ar: { common: arCommon, ai: arAi },
};

export function getDictionary(locale: TLocale, namespace: Namespace): Dict {
  return DICTIONARIES[locale][namespace];
}
