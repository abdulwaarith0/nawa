// Dictionary registry: locale + namespace -> plain JSON. Both locales must
// carry identical key sets (enforced by the i18n:check script + a unit test).

import type { TLocale } from "@nawa/contracts";

import arAi from "./ar/ai.json";
import arAuth from "./ar/auth.json";
import arCommon from "./ar/common.json";
import arCommunity from "./ar/community.json";
import arConsole from "./ar/console.json";
import arIntake from "./ar/intake.json";
import arJourney from "./ar/journey.json";
import arProfile from "./ar/profile.json";
import enAi from "./en/ai.json";
import enAuth from "./en/auth.json";
import enCommon from "./en/common.json";
import enCommunity from "./en/community.json";
import enConsole from "./en/console.json";
import enIntake from "./en/intake.json";
import enJourney from "./en/journey.json";
import enProfile from "./en/profile.json";

export type Namespace =
  | "common"
  | "ai"
  | "auth"
  | "console"
  | "intake"
  | "journey"
  | "community"
  | "profile";

type Dict = Record<string, unknown>;

export const DICTIONARIES: Record<TLocale, Record<Namespace, Dict>> = {
  en: {
    common: enCommon,
    ai: enAi,
    auth: enAuth,
    console: enConsole,
    intake: enIntake,
    journey: enJourney,
    community: enCommunity,
    profile: enProfile,
  },
  ar: {
    common: arCommon,
    ai: arAi,
    auth: arAuth,
    console: arConsole,
    intake: arIntake,
    journey: arJourney,
    community: arCommunity,
    profile: arProfile,
  },
};

export function getDictionary(locale: TLocale, namespace: Namespace): Dict {
  return DICTIONARIES[locale][namespace];
}
