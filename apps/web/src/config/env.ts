// The only file on the web side that reads process.env.

export const env = {
  environment: process.env.ENVIRONMENT ?? "development",
  // The public API URL for the browser is intentionally empty — relative paths
  // only, proxied by next.config's /api rewrite (keeps the session first-party).
  apiInternalUrl: process.env.API_INTERNAL_URL ?? "http://localhost:8000",
};

export const isDev = env.environment !== "production";
