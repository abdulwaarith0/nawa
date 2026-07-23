"use client";

import type { TLocale } from "@nawa/contracts";
import { createContext, useContext } from "react";

const LocaleContext = createContext<TLocale>("ar");

export function LocaleProvider({
  locale,
  children,
}: {
  locale: TLocale;
  children: React.ReactNode;
}) {
  return <LocaleContext.Provider value={locale}>{children}</LocaleContext.Provider>;
}

export function useLocale(): TLocale {
  return useContext(LocaleContext);
}
