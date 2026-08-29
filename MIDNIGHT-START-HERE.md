# START HERE — NAWA × Midnight Hackathon (fresh Claude session)

You are a fresh Claude Code session dedicated to a weekend hackathon build. This is SEPARATE from the user's polkadot-sdk / OSS PR work (handled in another tab) — ignore that entirely.

## Who / what
- User: **Abdulwaarith** (GitHub `abdulwaarith0`). Strong Rust/backend + TypeScript/Next.js.
- Project: **NAWA** — the user's **OWN** project. Repo `github.com/abdulwaarith0/nawa`, on disk `D:\Abdulwaarith\Desktop\nawa` (main app; `Documents\Nawa` is a design-system offshoot).
- NAWA = "The AI Operating System for innovation ecosystems": AI **intake screening**, **founder profiles**, cohort **journey** tracking, community, automated **reporting**. Stack: **Next.js 15 (web) + FastAPI/Python 3.12 (API) + Postgres 16 + pgvector + Redis + MinIO + LLM gateway (Claude)**. Arabic-first, RTL, bilingual. Has an **immutable audit log** + "AI never rejects, humans decide" ethos.
- Env: Windows 11, PowerShell primary + Git Bash. **Docker Desktop installed.**

## The hackathon
- **Midnight Hackathon, Aug 28–30** ($125 gift card per winning team member).
- Midnight = privacy blockchain (ZK proofs). Stack: **Compact** (a TypeScript-based DSL for the circuits) + **Midnight.js** (TS dApp framework) + a **proof server** (Docker) + **Preprod** testnet.
- **Track: AI** — *"AI apps that process sensitive info where models act on private data, and Midnight proves the rules were followed."* (Also fits the **Integrate Midnight** before/after track.)

## What to build — ONE feature, scoped
**Private, provable eligibility screening for NAWA.**
- An applicant proves via a Midnight ZK circuit that their private data meets a program's eligibility criteria, WITHOUT revealing the data.
- NAWA verifies the proof, marks the applicant "eligibility: proven," records the proof reference in its audit log, and AI screening proceeds — NAWA never sees the raw eligibility fields.

**Before:** applicant uploads DOB / nationality / funding history → NAWA sees it all → AI screens.
**After:** applicant submits a Midnight proof "eligible per criteria" → NAWA verifies, sees no raw fields → AI screens → audit log holds the proof.

### The circuit (Compact) — grow it, don't front-load complexity
- **MVP FIRST:** `age >= minAge` only — get the whole pipeline green end-to-end.
- **Then add:** `priorFunding <= cap` (another threshold).
- **Stretch:** nationality merkle-membership (drop if short on time).
Private (witness) inputs: age, priorFunding, stage, nationality. Public params: minAge, maxPriorFunding, stage range, allowedNationalitiesRoot. Emit a nullifier to prevent replay.

### Why low-friction
Compact is TS-based and Midnight.js is TS → it lands in NAWA's **Next.js** side. Do NOT touch the Python/FastAPI core — you're bolting a privacy layer onto the intake flow.

## Setup — Day 0 FIRST (working Midnight loop BEFORE touching NAWA)
Prereqs: **Node 22+** (use nvm), **Docker Desktop + Compose v2** (installed), the **Compact compiler** toolchain.
```bash
npx create-mn-app midnight-eligibility     # choose: Contract -> hello-world
cd midnight-eligibility && npm run setup    # boots local devnet (node+indexer+proof server) in Docker, compiles + deploys; no wallet/faucet needed locally
npm run cli                                 # interactive: call the contract's circuits
# testnet later: npm run setup -- --network preprod   (CLI generates a wallet + faucet URLs)
```
Goal for Day 0: hello-world compiling, deploying locally, callable via `npm run cli`. Read the sample Compact contract until the shape (ledger state + circuit defs) clicks. Do NOT start the real circuit until this loop works.

## Timeline (Fri–Sun)
- **Fri (3–4h):** setup + hello-world deploy/call + learn Compact.
- **Sat (bulk):** write the eligibility circuit (age check → funding cap), compile (`compactc`), deploy local, produce a **passing (eligible) + failing (ineligible)** proof pair (the core deliverable), then deploy to Preprod.
- **Sun:** wire a minimal Midnight.js "prove eligibility" step into NAWA's Next.js intake; verify + log the proof; build the before/after; record a 3-min demo; write the submission README.

**Cutlines if behind:** drop nationality merkle → drop full UI (one standalone page → POST to a NAWA API) → drop testnet (local devnet is fine) → mock the audit-log write (keep the "proof recorded, no PII" narrative).

## How to work (rules)
- **Scope discipline:** one working end-to-end proof of ONE criterion beats a half-built proof of five. Scope up only after the pipeline is green.
- Any public submission text (README / Devpost / comments): **plain human voice** — no emoji spam, no `## Problem/## Solution` AI scaffolding, no em-dash overload. Write like a dev typing quickly.
- Verify prereqs first: `node -v` (need 22+), `docker --version`.

## Submission checklist
- Public repo/branch showing the integration
- README with the **before/after** + AI-Track framing ("models act on private data, Midnight proves the rules were followed")
- 3-min demo: eligible proof passes, ineligible fails, NAWA verifies without seeing raw data
- The **Compact circuit** front-and-center (the technical substance)

## Docs
- Quickstart: https://docs.midnight.network/getting-started/quickstart
- First contract: https://docs.midnight.network/getting-started/hello-world
- Guides: https://docs.midnight.network/category/guides
- Midnight.js: https://github.com/midnightntwrk/midnight-js

## First move
Check `node -v` (need 22+) and `docker --version`, then run `npx create-mn-app` and get hello-world deploying locally. Report when the dev loop is green, then start the eligibility circuit at the single `age >= minAge` check.
