import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: {
    // Mirror tsconfig `@/*` → `src/*` so tests resolve the same paths as Next.
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    coverage: {
      provider: "v8",
      // Design-system code (primitives + layout shells) held to the bar;
      // barrels and feature wrappers (libs) excluded by explicit list.
      include: ["src/components/**", "src/layouts/**", "src/i18n/**", "src/helpers/**"],
      exclude: ["**/index.ts", "**/*.test.{ts,tsx}"],
      thresholds: { statements: 95, branches: 95, functions: 95, lines: 95 },
    },
  },
});
