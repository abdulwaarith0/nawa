# NAWA × Midnight — Eligibility Circuit Sketch

> ⚠️ **Read first.** This is a **logic sketch**, not copy-paste-final code. Compact's exact syntax (assert form, ledger types, stdlib names like `persistentHash`/`Set`/`MerkleTree`) shifts between compiler versions. **After you scaffold with `create-mn-app`, open the generated `hello-world`/`counter` `.compact` file — that is the source of truth for the current syntax** — and adapt the constructs below to match it. The INTENT of each line is commented so you can port it safely.

---

## Step 1 — MVP circuit: prove `age >= minAge` only
Goal: get the full pipeline (compile → prove → verify) green with the simplest possible circuit before adding anything.

```compact
pragma language_version >= 0.14;   // match whatever the scaffolded template declares
import CompactStandardLibrary;

// --- PUBLIC state (ledger): the program's eligibility criteria, on-chain & visible ---
export ledger minAge: Uint<8>;      // e.g. 18

// --- PRIVATE inputs (witness): supplied by the applicant at proving time, never revealed ---
witness applicantAge(): Uint<8>;

// --- CIRCUIT: verifies only if the private age satisfies the public rule ---
export circuit proveEligibility(): [] {   // [] = returns nothing; proof either verifies or fails
  const age = applicantAge();              // pull the private input
  assert(age >= minAge, "applicant below minimum age");
  // If the assert fails, no valid proof can be produced. A valid proof == "I know an age >= minAge",
  // and the raw age is never disclosed.
}
```
Wire `minAge` on deploy (e.g. 18). Then via `npm run cli`: prove with a witness age of 20 → **verifies**; prove with age 16 → **fails**. That passing/failing pair is your Day-1 deliverable.

---

## Step 2 — Add the funding cap + replay protection
Once the MVP proves/verifies, extend it.

```compact
pragma language_version >= 0.14;
import CompactStandardLibrary;

// Public criteria
export ledger minAge: Uint<8>;
export ledger maxPriorFunding: Uint<64>;
// Replay protection: track spent nullifiers so one applicant can't reuse a proof.
// (If `Set` isn't in your stdlib version, use a Map<Bytes<32>, Boolean> or a MerkleTree — check the template.)
export ledger usedNullifiers: Set<Bytes<32>>;

// Private inputs
witness applicantAge(): Uint<8>;
witness applicantPriorFunding(): Uint<64>;
witness applicantSecret(): Bytes<32>;   // random per applicant, used to derive the nullifier

export circuit proveEligibility(): [] {
  const age = applicantAge();
  const funding = applicantPriorFunding();

  assert(age >= minAge, "applicant below minimum age");
  assert(funding <= maxPriorFunding, "applicant exceeds prior-funding cap");

  // Derive a unique nullifier from the private secret and reject if already used.
  // `persistentHash` name/signature: verify against the stdlib the template imports.
  const nullifier = persistentHash<Bytes<32>>(applicantSecret());
  assert(!usedNullifiers.member(nullifier), "eligibility already proven for this applicant");
  usedNullifiers.insert(nullifier);
}
```

---

## Step 3 (STRETCH) — nationality in an allowed set
Skip unless the above is fully working. Model the allowed nationalities as a Merkle tree; the applicant proves membership without revealing which one.

```compact
// Public: root of the allowed-nationalities Merkle tree
export ledger allowedNationalitiesRoot: Field;

// Private: the applicant's nationality + the Merkle path proving it's in the set
witness applicantNationality(): Bytes<32>;
witness nationalityPath(): MerkleTreePath<Bytes<32>>;   // shape per stdlib

// inside proveEligibility, add:
assert(
  merkleTreePathValid(allowedNationalitiesRoot, applicantNationality(), nationalityPath()),
  "nationality not in allowed set"
);
```
(Merkle helpers are the most version-sensitive part — leave for last, and lean on the stdlib docs.)

---

## TypeScript side (Midnight.js) — the shape, not the final API
After `compactc` compiles the contract, `create-mn-app` generates a TS module with typed circuit callers. Exact API names come from the generated code + the quickstart; the flow is:

```ts
// 1. Providers: proof server + node + indexer (create-mn-app wires these; MidnightProviders object)
// 2. Deploy or connect to the contract (deployed by `npm run setup`)
// 3. Build the private witnesses for THIS applicant:
const witnesses = {
  applicantAge: () => 20n,
  applicantPriorFunding: () => 0n,
  applicantSecret: () => randomBytes32(),
};
// 4. Call the circuit -> the proof server produces the ZK proof, submitted as a tx:
await contract.circuits.proveEligibility(witnesses);   // name shape; verify vs generated module
// A successful tx == verified eligibility. Catch the failure for ineligible inputs.
```
> Don't hand-write the provider wiring — reuse what `create-mn-app` generated for hello-world and swap in this contract. Grep the generated files for `circuits`, `witnesses`, and `MidnightProviders`.

---

## NAWA integration point
- NAWA intake today collects raw eligibility fields. Add a step **before** that: an "Prove eligibility" action in the Next.js intake page that builds the witnesses from the applicant's inputs **client-side** and calls `proveEligibility`.
- On success, NAWA marks the applicant `eligibility: proven`, stores the **tx/proof reference** (NOT the raw fields) in its existing audit log, and lets AI screening proceed.
- **Before/after** is now literal: the "after" path stores a proof reference where the "before" path stored DOB/nationality/funding.
- Time-boxed fallback: a single standalone Next.js page that runs the circuit and `POST`s `{applicantId, proofRef, eligible:true}` to a NAWA API endpoint — enough to demo the before/after without touching the full intake flow.

## Test cases (your demo backbone)
1. **Eligible:** age 20, funding 0 → proof verifies → NAWA marks proven, logs proof, no PII stored. ✅
2. **Ineligible (age):** age 16 → proof fails → NAWA rejects, no data leaked. ✅
3. **Ineligible (funding):** funding over cap → proof fails. ✅
4. **Replay:** same applicant proves twice → second fails on the nullifier. ✅ (if Step 2 done)

## Porting checklist (do this as you go)
- [ ] Match `pragma` version to the scaffolded template
- [ ] Confirm `assert(cond, "msg")` syntax vs the template
- [ ] Confirm ledger types (`Uint<N>`, `Set`/`Map`/`MerkleTree`, `Field`) exist in your stdlib version
- [ ] Confirm `persistentHash` / merkle helper names
- [ ] Confirm the generated TS circuit-caller + witness shape
