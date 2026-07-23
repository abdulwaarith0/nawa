import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    coverage: {
      provider: "v8",
      // Design-system code this slice introduces; barrels excluded by explicit list.
      include: ["src/components/**", "src/i18n/**", "src/helpers/**"],
      exclude: ["**/index.ts", "**/*.test.{ts,tsx}"],
      thresholds: { statements: 95, branches: 95, functions: 95, lines: 95 },
    },
  },
});
