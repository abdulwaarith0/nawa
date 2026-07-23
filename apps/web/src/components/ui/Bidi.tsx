// Bidi isolation for mixed-direction content (design-system §4.5). All
// user-generated display fields (names, venture names, request titles) render
// inside <bdi> since their direction can't be known in advance.

export function Bidi({
  children,
  dir = "auto",
  lang,
}: {
  children: React.ReactNode;
  dir?: "auto" | "ltr" | "rtl";
  lang?: string;
}) {
  return (
    <bdi dir={dir} lang={lang}>
      {children}
    </bdi>
  );
}
