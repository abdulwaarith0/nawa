// Diffs the key sets of src/i18n/ar/*.json vs src/i18n/en/*.json and exits
// non-zero on any asymmetric key (design-system DoD §5). Plural nodes (all-CLDR
// category keys) are treated as a single leaf, since Arabic legitimately carries
// more plural categories than English.

import { readFileSync, readdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const i18nDir = resolve(here, "..", "src", "i18n");
const CLDR = new Set(["zero", "one", "two", "few", "many", "other"]);

function isPluralNode(obj) {
  const keys = Object.keys(obj);
  return keys.length > 0 && keys.every((k) => CLDR.has(k));
}

function collectKeys(obj, prefix = "") {
  if (obj === null || typeof obj !== "object") return [prefix];
  if (isPluralNode(obj)) return [prefix];
  return Object.entries(obj).flatMap(([k, v]) => collectKeys(v, prefix ? `${prefix}.${k}` : k));
}

function keysFor(locale, namespace) {
  const raw = JSON.parse(readFileSync(join(i18nDir, locale, `${namespace}.json`), "utf8"));
  return new Set(collectKeys(raw));
}

const namespaces = readdirSync(join(i18nDir, "en"))
  .filter((f) => f.endsWith(".json"))
  .map((f) => f.replace(/\.json$/, ""));

let failed = false;
for (const ns of namespaces) {
  const en = keysFor("en", ns);
  const ar = keysFor("ar", ns);
  const missingInAr = [...en].filter((k) => !ar.has(k));
  const missingInEn = [...ar].filter((k) => !en.has(k));
  if (missingInAr.length || missingInEn.length) {
    failed = true;
    console.error(`\n[${ns}] key mismatch:`);
    if (missingInAr.length) console.error(`  missing in ar: ${missingInAr.join(", ")}`);
    if (missingInEn.length) console.error(`  missing in en: ${missingInEn.join(", ")}`);
  }
}

if (failed) {
  console.error("\ni18n:check FAILED — locale key sets are not symmetric.");
  process.exit(1);
}
console.log(`i18n:check passed (${namespaces.length} namespaces, symmetric key sets).`);
