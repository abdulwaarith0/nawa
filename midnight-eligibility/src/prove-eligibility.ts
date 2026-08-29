/**
 * Prove NAWA eligibility on the local Midnight devnet.
 *
 * Deploys a fresh eligibility contract whose PUBLIC criteria (minAge,
 * maxPriorFunding) live on-chain, then proves `proveEligibility()` using
 * PRIVATE applicant data (age, priorFunding, secret) supplied as witnesses.
 * The raw data is never sent to the chain — only the pass/fail ZK proof is.
 * A per-applicant secret derives an on-chain nullifier for replay protection.
 *
 *   MIN_AGE=18 MAX_FUNDING=100000 AGE=20 FUNDING=0 npm run prove   -> eligible
 *   AGE=16 ...                                                     -> below min age
 *   FUNDING=200000 ...                                             -> over funding cap
 *   AGE=20 FUNDING=0 REPLAY=1 ...                                  -> proves twice; 2nd blocked
 *
 * A verifying proof == "I know data meeting every public rule" without
 * disclosing it. A failing rule makes the circuit assert fail, so no valid
 * proof can be produced and the call throws — which is the whole point.
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import { randomBytes } from 'node:crypto';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { WebSocket } from 'ws';
import * as Rx from 'rxjs';

import { deployContract, findDeployedContract } from '@midnight-ntwrk/midnight-js-contracts';
import { httpClientProofProvider } from '@midnight-ntwrk/midnight-js-http-client-proof-provider';
import { indexerPublicDataProvider } from '@midnight-ntwrk/midnight-js-indexer-public-data-provider';
import { levelPrivateStateProvider } from '@midnight-ntwrk/midnight-js-level-private-state-provider';
import { NodeZkConfigProvider } from '@midnight-ntwrk/midnight-js-node-zk-config-provider';
import { CompiledContract } from '@midnight-ntwrk/midnight-js-protocol/compact-js';

import { resolveNetwork, getOrCreateWallet } from './network';
import { createWallet, persistWalletState, unshieldedToken, type WalletContext } from './wallet';

// @ts-expect-error Required for wallet sync
globalThis.WebSocket = WebSocket;

// Private state for this contract: the applicant's private fields. The
// witnesses read from here and hand values to the circuit — never the ledger.
type EligibilityPrivateState = { age: bigint; priorFunding: bigint; secret: Uint8Array };
const PRIVATE_STATE_ID = 'eligibilityPrivateState';

// ─── Inputs ──────────────────────────────────────────────────────────────────
// Public criteria (on-chain):
const MIN_AGE = BigInt(process.env.MIN_AGE ?? '18');
const MAX_FUNDING = BigInt(process.env.MAX_FUNDING ?? '100000');
// Private applicant data (witnessed):
const AGE_RAW = process.env.AGE;
if (AGE_RAW === undefined) {
  console.error('\n  Set AGE (private applicant age). e.g. MIN_AGE=18 MAX_FUNDING=100000 AGE=20 FUNDING=0 npx tsx src/prove-eligibility.ts\n');
  process.exit(2);
}
const AGE = BigInt(AGE_RAW);
const FUNDING = BigInt(process.env.FUNDING ?? '0');
// Per-applicant secret that derives the on-chain nullifier. Random each run
// unless SECRET (64 hex chars) is pinned. REPLAY=1 proves twice with the same
// secret to demonstrate replay protection (the second attempt must fail).
const SECRET = process.env.SECRET ? Uint8Array.from(Buffer.from(process.env.SECRET, 'hex')) : new Uint8Array(randomBytes(32));
const REPLAY = process.env.REPLAY === '1';

const { network, config: networkConfig } = resolveNetwork();
const SEED = getOrCreateWallet(network).seed;

// ─── Compiled contract + witnesses ─────────────────────────────────────────────
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const zkConfigPath = path.resolve(__dirname, '..', 'contracts', 'managed', 'eligibility');
const contractPath = path.join(zkConfigPath, 'contract', 'index.js');
if (!fs.existsSync(contractPath)) {
  console.error('\n  Eligibility contract not compiled. Run: compact compile contracts/eligibility.compact contracts/managed/eligibility\n');
  process.exit(1);
}
const Eligibility = await import(pathToFileURL(contractPath).href);

// Each witness returns [unchanged private state, the private value].
const witnesses = {
  applicantAge: (ctx: { privateState: EligibilityPrivateState }): [EligibilityPrivateState, bigint] => [
    ctx.privateState,
    ctx.privateState.age,
  ],
  applicantPriorFunding: (ctx: { privateState: EligibilityPrivateState }): [EligibilityPrivateState, bigint] => [
    ctx.privateState,
    ctx.privateState.priorFunding,
  ],
  applicantSecret: (ctx: { privateState: EligibilityPrivateState }): [EligibilityPrivateState, Uint8Array] => [
    ctx.privateState,
    ctx.privateState.secret,
  ],
};

const compiledContract = CompiledContract.make('eligibility', Eligibility.Contract).pipe(
  (self: any) => CompiledContract.withWitnesses(self, witnesses as any),
  CompiledContract.withCompiledFileAssets(zkConfigPath),
);

// ─── Providers (mirrors deploy.ts) ─────────────────────────────────────────────
async function createProviders(walletCtx: WalletContext) {
  const privateStatePassword = process.env.PRIVATE_STATE_PASSWORD?.trim() || 'Local-Devnet-Development-Placeholder-1';
  const walletProvider = {
    getCoinPublicKey: () => walletCtx.shieldedSecretKeys.coinPublicKey,
    getEncryptionPublicKey: () => walletCtx.shieldedSecretKeys.encryptionPublicKey,
    async balanceTx(tx: any, ttl?: Date) {
      const recipe = await walletCtx.wallet.balanceUnboundTransaction(
        tx,
        { shieldedSecretKeys: walletCtx.shieldedSecretKeys, dustSecretKey: walletCtx.dustSecretKey },
        { ttl: ttl ?? new Date(Date.now() + 30 * 60 * 1000) },
      );
      return walletCtx.wallet.finalizeRecipe(recipe);
    },
    submitTx: (tx: any) => walletCtx.wallet.submitTransaction(tx) as any,
  };
  const zkConfigProvider = new NodeZkConfigProvider(zkConfigPath);
  const accountId = walletCtx.unshieldedKeystore.getBech32Address().toString();
  return {
    privateStateProvider: levelPrivateStateProvider({
      privateStateStoreName: 'eligibility-state',
      accountId,
      privateStoragePasswordProvider: () => privateStatePassword,
    }),
    publicDataProvider: indexerPublicDataProvider(networkConfig.indexer, networkConfig.indexerWS),
    zkConfigProvider,
    proofProvider: httpClientProofProvider(networkConfig.proofServer, zkConfigProvider),
    walletProvider,
    midnightProvider: walletProvider,
  };
}

// ─── DUST readiness (mirrors deploy.ts) ─────────────────────────────────────────
async function ensureDust(walletCtx: WalletContext): Promise<void> {
  const dustState = await Rx.firstValueFrom(walletCtx.wallet.state().pipe(Rx.filter((s: any) => s.isSynced)));
  const unregistered = dustState.unshielded.availableCoins.filter((c: any) => !c.meta?.registeredForDustGeneration);
  if (unregistered.length > 0) {
    const recipe = await walletCtx.wallet.registerNightUtxosForDustGeneration(
      unregistered,
      walletCtx.unshieldedKeystore.getPublicKey(),
      (payload: any) => walletCtx.unshieldedKeystore.signData(payload),
    );
    const finalized = await walletCtx.wallet.finalizeRecipe(recipe);
    await walletCtx.wallet.submitTransaction(finalized);
  }
  if (dustState.dust.balance(new Date()) === 0n) {
    await Rx.firstValueFrom(
      walletCtx.wallet.state().pipe(
        Rx.throttleTime(5000),
        Rx.filter((s: any) => s.isSynced),
        Rx.filter((s: any) => s.dust.balance(new Date()) > 0n),
      ),
    );
  }
}

// ─── Main ──────────────────────────────────────────────────────────────────────
async function main() {
  console.log('\n──────────────────────────────────────────────────────────────');
  console.log('  NAWA × Midnight — prove eligibility');
  console.log(`  Public criteria (on-chain):   minAge = ${MIN_AGE}, maxPriorFunding = ${MAX_FUNDING}`);
  console.log(`  Private witnesses (never sent): age = ${AGE}, priorFunding = ${FUNDING}`);
  console.log('──────────────────────────────────────────────────────────────\n');

  const walletCtx = await createWallet({ network, networkConfig, seed: SEED });
  console.log('  Syncing wallet with devnet...');
  await walletCtx.wallet.waitForSyncedState();
  await persistWalletState(network, walletCtx);
  await ensureDust(walletCtx);

  const providers = await createProviders(walletCtx);

  const initialPrivateState: EligibilityPrivateState = { age: AGE, priorFunding: FUNDING, secret: SECRET };

  console.log('  Deploying eligibility contract (sets public criteria)...');
  const deployed: any = await deployContract(providers, {
    compiledContract: compiledContract as any,
    args: [MIN_AGE, MAX_FUNDING],
    privateStateId: PRIVATE_STATE_ID,
    initialPrivateState,
  });
  const address = deployed.deployTxData.public.contractAddress;
  console.log(`  Contract: ${address}\n`);

  // Connect (fresh) to the deployed contract, synced to the indexer's latest
  // ledger state. Re-connecting before each attempt guarantees the circuit
  // runs against current state — important for the replay check, which must
  // see the nullifier written by the first proof.
  async function connect() {
    // The indexer only exposes contract state once it has indexed the tx;
    // calling too early yields "expected instance of StateValue".
    console.log('  Waiting for indexer to expose latest contract state...');
    for (let i = 0; i < 60; i++) {
      const s = await providers.publicDataProvider.queryContractState(address);
      if (s) break;
      await new Promise((r) => setTimeout(r, 1000));
    }
    return findDeployedContract(providers, {
      compiledContract: compiledContract as any,
      contractAddress: address,
      privateStateId: PRIVATE_STATE_ID,
      initialPrivateState,
    }) as any;
  }

  // Returns 'eligible' | { rejected: reason } | throws for real errors.
  async function attemptProof(found: any): Promise<{ ok: true; txId: string } | { ok: false; reason: string }> {
    try {
      const tx = await found.callTx.proveEligibility();
      return { ok: true, txId: tx.public.txId };
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      // A failing circuit assert throws "failed assert: <message>". Only that
      // counts as a rejection; anything else is a real bug and must surface.
      const m = msg.match(/failed assert:\s*(.*)/i);
      if (m) return { ok: false, reason: m[1].split('\n')[0].trim() };
      console.error('\n  ❗ Unexpected error while proving (NOT an eligibility rejection):');
      console.error(`     ${msg.split('\n')[0]}`);
      if (process.env.DEBUG_STACK) console.error(err instanceof Error ? err.stack : err);
      throw err;
    }
  }

  // ── First proof attempt ──
  console.log('  Generating eligibility proof (proof server)...');
  const r1 = await attemptProof(await connect());
  if (r1.ok) {
    console.log('\n  ✅ ELIGIBLE — proof verified. The chain accepted the tx without ever');
    console.log('     seeing the applicant\'s private data.');
    console.log(`     Tx: ${r1.txId}`);
    console.log(`     Proof reference (for NAWA audit log): ${address}@${r1.txId}\n`);
  } else {
    console.log('\n  ⛔ INELIGIBLE — no valid proof could be produced.');
    console.log('     A circuit rule failed, so proving aborted. NAWA rejects, and no');
    console.log('     private data ever left the client.');
    console.log(`     (reason: ${r1.reason})\n`);
  }

  // ── Replay attempt (same secret → same nullifier → must be rejected) ──
  if (REPLAY && r1.ok) {
    console.log('  ── Replay: proving AGAIN with the SAME secret ──');
    // Give the indexer time to reflect the nullifier written by the first proof.
    await new Promise((r) => setTimeout(r, 8000));
    const r2 = await attemptProof(await connect());
    if (!r2.ok && /already proven/i.test(r2.reason)) {
      console.log('\n  ✅ REPLAY BLOCKED — the second proof was correctly rejected.');
      console.log(`     (reason: ${r2.reason})\n`);
      await walletCtx.wallet.stop();
      process.exit(0);
    }
    console.error('\n  ❗ REPLAY NOT BLOCKED — the second proof should have failed on the nullifier.');
    console.error(`     ${r2.ok ? `it verified (tx ${r2.txId})` : `rejected for wrong reason: ${r2.reason}`}\n`);
    await walletCtx.wallet.stop();
    process.exit(4);
  }

  await walletCtx.wallet.stop();
  process.exit(r1.ok ? 0 : 1);
}

main().catch(async (err) => {
  console.error('\n  Unexpected error:', err instanceof Error ? err.message : err);
  process.exit(3);
});
