"use client";

import { type ReactNode, useMemo } from "react";

export interface IProps {
  children: ReactNode;
  dir?: "auto" | "ltr" | "rtl";
  lang?: string;
}

// Bidi isolation for mixed-direction content (design-system §4.5). All
// user-generated display fields (names, venture names, request titles) render
// inside <bdi> since their direction can't be known in advance.
export default function Bidi({ children, dir = "auto", lang }: IProps) {
  return useMemo(
    () => (
      <bdi dir={dir} lang={lang}>
        {children}
      </bdi>
    ),
    [children, dir, lang],
  );
}
