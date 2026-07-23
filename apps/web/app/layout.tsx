import type { Metadata } from "next";
import "../src/styles/tokens.css";
import "../src/styles/base.css";

export const metadata: Metadata = {
  title: "NAWA",
  description: "The AI Operating System for Program's innovation-program ecosystem.",
};

// Arabic is the default locale for anonymous visitors (design-system §5.1);
// RTL-first. Locale resolution proper arrives with the i18n layer.
//
// Fonts (IBM Plex Sans Arabic + Archivo) are wired via CSS variable fallbacks
// in tokens.css so the app boots without a build-time font fetch; next/font
// (or bundled woff2 via next/font/local) can define --font-plex-arabic /
// --font-archivo later to swap in the exact faces.
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ar" dir="rtl">
      <body>{children}</body>
    </html>
  );
}
