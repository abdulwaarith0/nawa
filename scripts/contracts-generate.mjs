// Runs the full contracts pipeline end-to-end (architecture §4/§6):
//   1. Python: export the OpenAPI schema + generated iam.ts (app built offline)
//   2. TS: openapi-typescript turns openapi.json into src/gen/api.ts
// Deterministic — reruns are no-ops. CI runs this then `git diff --exit-code`.

import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const apiDir = resolve(repoRoot, "services", "api");

function run(cmd, args, cwd, env) {
  const res = spawnSync(cmd, args, {
    cwd,
    stdio: "inherit",
    shell: process.platform === "win32",
    env: { ...process.env, ...env },
  });
  if (res.status !== 0) {
    console.error(`\nFAILED: ${cmd} ${args.join(" ")} (exit ${res.status})`);
    process.exit(res.status ?? 1);
  }
}

// 1. Python export (offline — no DB/Redis). A dev JWT secret satisfies settings.
run("uv", ["run", "python", "-m", "nawa_api.scripts.export_openapi"], apiDir, {
  ENVIRONMENT: process.env.ENVIRONMENT ?? "development",
  JWT_SECRET: process.env.JWT_SECRET ?? "change-me-in-development-only",
});

// 2. TS generation from the fresh openapi.json.
run("pnpm", ["--filter", "@nawa/contracts", "codegen"], repoRoot);

console.log("\nContracts generated.");
