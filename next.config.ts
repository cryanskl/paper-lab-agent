import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // better-sqlite3 must run in the Node.js runtime, not the Edge runtime.
  serverExternalPackages: ["better-sqlite3"],
  experimental: {
    typedRoutes: false,
  },
};

export default nextConfig;
