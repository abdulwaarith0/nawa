# NAWA × Midnight — private, provable eligibility screening

A zero-knowledge eligibility check for [NAWA](../README.md)'s intake, built on
[Midnight](https://midnight.network) with the Compact language.

An applicant can prove they **meet a program's eligibility criteria** — old
enough, under a prior-funding cap — **without revealing their actual age or
funding history**. The criteria live in public on-chain state so anyone can
audit what applicants are held to; the applicant's real numbers stay on their
own device and never touch the chain. A valid proof means only *"I know values
that satisfy the rules"* — nothing more leaks.

This fits NAWA's "AI never rejects, humans decide" ethos and its immutable
audit log: intake can record *that* an applicant cleared the bar, with a proof
reference, without ever storing the sensitive inputs behind that decision.

## Why this matters

Intake screening normally means handing over raw personal data — date of
birth, past grant amounts — to a platform that stores it. That is a privacy and
liability burden, and it is often more than a yes/no decision actually needs.
Here the decision is computed **client-side inside a ZK proof**. The platform
receives a verifiable "eligible / not eligible", plus a one-time reference it
can drop in the audit log. The raw inputs never leave the applicant.

## How it works

The contract (`contracts/eligibility.compact`) splits state into public and
private:

- **Public ledger** (auditable on-chain): `minAge`, `maxPriorFunding`, and a set
  of spent `usedNullifiers`. Set once at deploy time — these are the rules.
- **Private witnesses** (supplied client-side at proving time, never disclosed):
  the applicant's `age`, `priorFunding`, and a per-applicant `secret`.

The `proveEligibility` circuit asserts:

1. `age >= minAge`
2. `priorFunding <= maxPriorFunding`
3. the applicant hasn't already proven eligibility — it derives a
   domain-separated **nullifier** from the private secret and rejects a repeat.

Only the nullifier (a one-way hash that reveals nothing about the secret) is
written on-chain. Producing the proof requires knowing private inputs that
satisfy every rule; verification never sees those inputs.

## Run the demo

**Prerequisites:** Node 20+, Docker (Compose v2), and the Compact compiler
pinned in `.compact-version`. On Windows the Compact toolchain runs under WSL2
Ubuntu — run every command there.

```bash
npm install
npm run compile:eligibility     # -> contracts/managed/eligibility/
docker compose up -d proof-server   # local ZK proof server on :6300
```

The driver deploys a fresh contract and proves against it. Inputs are passed as
env vars — the public criteria (`MIN_AGE`, `MAX_FUNDING`) and the private
witnesses (`AGE`, `FUNDING`):

```bash
# 1) eligible: age 20 clears minAge 18, funding 0 under the cap
MIN_AGE=18 MAX_FUNDING=100000 AGE=20 FUNDING=0 npm run prove -- --network undeployed

# 2) replay guard: deploy once, prove twice with the same secret — 2nd is rejected
MIN_AGE=18 MAX_FUNDING=100000 AGE=20 FUNDING=0 REPLAY=1 npm run prove -- --network undeployed

# 3) underage: age 16 fails minAge 18
MIN_AGE=18 MAX_FUNDING=100000 AGE=16 FUNDING=0 npm run prove -- --network undeployed

# 4) over the cap: prior funding 200000 exceeds 100000
MIN_AGE=18 MAX_FUNDING=100000 AGE=20 FUNDING=200000 npm run prove -- --network undeployed
```

### Verified output

All four cases pass end-to-end on the local devnet:

| Case | Inputs | Result |
| --- | --- | --- |
| Eligible | age 20, fund 0 | ✅ **ELIGIBLE — proof verified** |
| Replay | same secret, twice | ✅ **REPLAY BLOCKED** on the nullifier |
| Underage | age 16 | ⛔ **INELIGIBLE** — "applicant below minimum age" |
| Over cap | fund 200000 | ⛔ **INELIGIBLE** — "applicant exceeds prior-funding cap" |

The eligible run prints a proof reference for the audit log, e.g.
`460870b0…a568a2d5@005aa3a8…024ba5` (`<contractAddress>@<txId>`).

## Testnet status

The circuit and driver are verified end-to-end on the **local devnet**
(node + indexer + proof-server via `docker-compose.yml`). A deploy to the
public **preview** testnet was attempted — the wallet funds and generates DUST
fine — but the preview indexer is currently unstable for the deploy path (its
GraphQL responses close mid-stream), so on-chain deploys don't complete
reliably right now. The preview wallet stays funded and persisted, so a retry
once that indexer stabilizes is a one-command re-run:

```bash
MIN_AGE=18 MAX_FUNDING=100000 AGE=20 FUNDING=0 npm run prove -- --network preview
```

## Project layout

```
midnight-eligibility/
├── contracts/
│   ├── eligibility.compact     # the ZK eligibility circuit
│   └── hello-world.compact     # create-mn-app starter, kept as a syntax reference
├── src/
│   ├── prove-eligibility.ts    # deploy eligibility + prove the four cases
│   ├── network.ts              # network selection + state file management
│   ├── wallet.ts               # wallet construction + sync-state cache
│   ├── deploy.ts               # generic contract deploy
│   ├── cli.ts                  # interact with a deployed contract
│   └── check-balance.ts        # NIGHT / DUST balance
├── scripts/e2e-check.ts        # smoke + read-back
└── docker-compose.yml          # node + indexer + proof-server
```

## Networks

| Network | Use | Faucet |
| --- | --- | --- |
| `undeployed` | Local devnet in `docker-compose.yml`; genesis seed, no funding needed | — |
| `preview` | Public preview testnet | `https://midnight-tmnight-preview.nethermind.dev` |
| `preprod` | Public preprod testnet | `https://midnight-tmnight-preprod.nethermind.dev` |

The active network is **sticky** — the last `--network <name>` you used stays
active for later commands. Public networks generate a fresh 24-word wallet on
first use, stored in `.midnight-state.json` (gitignored). Fund it from the
faucet; the driver polls the balance and continues once tNIGHT lands.
`.midnight-wallet-state/<network>/` caches synced state so later runs catch up
from the last block instead of replaying from genesis.

> **Local devnet uses a well-known genesis seed** (`0000…0001`) so pre-minted
> NIGHT is available immediately. Never use that seed against a network that
> handles real value.

## Scripts

| Script | Description |
| --- | --- |
| `npm run compile:eligibility` | Compile the eligibility circuit. |
| `npm run prove` | Deploy the eligibility contract and prove (env-driven; see the demo). |
| `npm run setup` | One-shot: start devnet, compile, deploy. |
| `npm run cli` | Interactive CLI against a deployed contract. |
| `npm run check-balance` | Print the active wallet's NIGHT / DUST balances. |
| `npm run test:e2e` | Reconnect to a deployed contract and read its ledger state. |
| `npm run clean` | Remove compiled artifacts and generated wallet/devnet state. |

## Compact compiler

Pin the compiler to the version in `.compact-version`:

```bash
compact update <version>
compact use <version>
```
