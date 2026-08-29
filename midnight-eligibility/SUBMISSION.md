# NAWA × Midnight — submission writeup

## Inspiration

NAWA is an AI platform that runs intake and screening for innovation programs.
Intake normally means applicants hand over sensitive personal data — age, past
grant history — which the platform then has to store and protect, even when the
decision itself only needs a yes/no. That is a privacy and liability burden, and
it sits awkwardly next to NAWA's "AI never rejects, humans decide" ethos and its
immutable audit log. Midnight's zero-knowledge model was a clean fit: prove the
applicant meets the criteria without ever collecting the data behind it.

## What it does

An applicant proves they satisfy a program's eligibility rules — old enough,
under a prior-funding cap — **without revealing their real age or funding
amount**. The rules live in public on-chain state, so anyone can audit what
applicants are held to. The applicant's actual numbers stay on their device and
never touch the chain. A per-applicant nullifier makes each eligibility proof
one-time, so the same person can't quietly prove twice.

The output is a proof reference (`contractAddress@txId`) that NAWA's intake can
drop straight into its audit log: a verifiable record that someone cleared the
bar, with none of the sensitive inputs.

## How we built it

- **Circuit** (`contracts/eligibility.compact`, Compact): public ledger holds
  `minAge`, `maxPriorFunding`, and a set of spent nullifiers. `age`,
  `priorFunding`, and a `secret` are private witnesses. `proveEligibility`
  asserts the two rules, derives a domain-separated nullifier from the secret,
  and rejects a replay.
- **Driver** (`src/prove-eligibility.ts`, Midnight.js): deploys a fresh contract
  with the public criteria, generates the ZK proof against private inputs, and
  reports eligible / ineligible. It also handles wallet setup, DUST generation,
  and the replay demo.
- **Local devnet** via `docker-compose.yml` (node + indexer + proof-server) for
  a full compile → deploy → prove → verify loop.

## Challenges we ran into

- **Compact is private-by-default** — every input, including constructor params,
  is private until you explicitly `disclose()` it. Getting the public/private
  split right (rules public, applicant data private) took some iteration.
- **Runtime version pinning** — the compiler, `compact-runtime`, and the native
  `onchain-runtime` had to line up exactly, and two physical copies of the
  native runtime caused `StateValue` mismatch errors on every circuit call until
  we de-duped them.
- **Public testnet indexer instability** — deploying to the preview testnet is
  blocked right now by the preview indexer closing its GraphQL responses
  mid-stream during deploy (confirmed against Midnight's own note that the v4
  indexer isn't ready on preview yet). The wallet funds and generates DUST fine;
  the deploy just can't read back reliably. We verified everything end-to-end on
  the local devnet instead, and left a one-command retry for when preview
  stabilizes.

## Accomplishments we're proud of

- A working ZK eligibility check with a real privacy guarantee, verified across
  four cases (eligible, replay-blocked, underage, over-cap) — see `DEMO.md`.
- A nullifier-based replay guard, so eligibility is one-shot per applicant.
- A clean integration story with NAWA's existing audit log via the proof
  reference.

## What we learned

- How to model a real access-control decision as a ZK circuit, and where the
  public/private boundary should sit.
- The practical realities of Midnight's toolchain: version pinning, DUST as the
  fee token, and how the wallet/indexer/proof-server pieces fit together.

## What's next

- Land the on-chain deploy on a public testnet once the indexer stabilizes (the
  retry is already wired).
- Wire the proof step into NAWA's intake flow so a screening records the proof
  reference in the audit log automatically.
- Extend the criteria beyond age/funding (residency, program-specific gates)
  while keeping every applicant input private.

## Built with

Compact · Midnight.js · TypeScript · Docker · a local Midnight devnet
(node + indexer + proof-server).
