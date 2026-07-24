import { defineConfig, devices } from "@playwright/test";

// e2e config (06-intake-copilot.md §9/§10.12). Runs against the seeded dev
// stack — reuses an already-running `pnpm dev` server rather than starting a
// second one, since the API + web dev servers are long-lived local processes
// (docker postgres/redis/minio + `uv run uvicorn` + `next dev`), not
// something this suite owns the lifecycle of.
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["html", { open: "never" }]],
  use: {
    baseURL: "http://localhost:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "pnpm dev",
    url: "http://localhost:3000",
    reuseExistingServer: true,
    timeout: 60_000,
  },
});
