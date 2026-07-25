// Mirrors decide_application.py's `_DECIDABLE_STATUSES` exactly — a human
// decision can only be recorded once an application has actually been AI-
// scored (status "scored") or already has a decision on it ("shortlisted",
// "waitlisted", "decided"). The API rejects anything else with a bare
// "Invalid fields" error, so every decision surface gates on this first.
export const DECIDABLE_APPLICATION_STATUSES = new Set([
  "scored",
  "shortlisted",
  "waitlisted",
  "decided",
]);

export function isDecidableStatus(status: string): boolean {
  return DECIDABLE_APPLICATION_STATUSES.has(status);
}
