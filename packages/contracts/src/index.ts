// Public surface of @nawa/contracts. Re-exports generated types + the IAM
// vocabulary + the envelope + the Routes tree. Hand-written files here are
// limited to re-exports, the Routes const tree, and zod refinements — never
// parallel definitions of anything the API owns.

export type { paths, components, operations } from "./gen/api";
export * from "./gen/iam";
export * from "./envelope";
export * from "./routes";

// The user/session locale union, mirrored from the API's `language` field.
export type TLocale = "ar" | "en";
