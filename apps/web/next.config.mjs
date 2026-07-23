/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // The browser only ever calls relative /api/* on its own origin (keeps the
  // session cookie first-party); this rewrite proxies to the FastAPI service.
  async rewrites() {
    const apiInternalUrl = process.env.API_INTERNAL_URL ?? "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${apiInternalUrl}/api/v1/:path*`,
      },
    ];
  },
  transpilePackages: ["@nawa/contracts", "@nawa/api-client"],
};

export default nextConfig;
