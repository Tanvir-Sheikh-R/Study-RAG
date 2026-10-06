import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // The dev server is reached as 127.0.0.1 by tooling and as localhost in the browser;
  // without this, Next blocks its own dev resources for the 127.0.0.1 origin.
  allowedDevOrigins: ["127.0.0.1", "localhost"],
};

export default nextConfig;
