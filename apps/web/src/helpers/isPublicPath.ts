// Shared by the edge middleware and the browser api-client: is `pathname`
// reachable without a session? Both need the same prefix-matching semantics
// (exact "/" only for the root; exact-or-nested-prefix for everything else),
// so this is a plain, dependency-free function importable from either the
// Edge runtime (middleware.ts) or the browser (apiClient.ts).
function matchesPrefix(pathname: string, prefixes: readonly string[]): boolean {
  return prefixes.some((p) =>
    p === "/" ? pathname === "/" : pathname === p || pathname.startsWith(`${p}/`),
  );
}

export function isPublicPath(pathname: string, publicPrefixes: readonly string[]): boolean {
  return matchesPrefix(pathname, publicPrefixes);
}
