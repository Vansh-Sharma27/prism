import type { NextConfig } from "next";

const backendBase = (process.env.PRISM_BACKEND_URL || "http://127.0.0.1:5000").replace(/\/$/, "");

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${backendBase}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
