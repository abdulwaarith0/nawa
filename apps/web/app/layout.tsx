import { LocaleProvider } from "@/i18n/LocaleProvider";
import type { TLocale } from "@nawa/contracts";
import type { Metadata } from "next";
import { cookies } from "next/headers";
import "@/styles/tokens.css";
import "@/styles/base.css";

export const metadata: Metadata = {
  title: "NAWA",
  description: "The AI Operating System for innovation-program ecosystems.",
};

// Locale resolution: nw_locale cookie -> ar (the default for anonymous
// visitors). Arabic is RTL-first. The switcher (LocaleSwitcher) sets the cookie.
// Fonts are wired via CSS-variable fallbacks in tokens.css so the app boots
// without a build-time font fetch.
export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const cookieStore = await cookies();
  const locale: TLocale = cookieStore.get("nw_locale")?.value === "en" ? "en" : "ar";
  const dir = locale === "ar" ? "rtl" : "ltr";

  return (
    <html lang={locale} dir={dir}>
      <body>
        <LocaleProvider locale={locale}>{children}</LocaleProvider>
      </body>
    </html>
  );
}
