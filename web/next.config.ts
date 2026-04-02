import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Static export for `parsemux serve --ui` (served by FastAPI)
  output: "export",

  // Proxy API calls to local backend in development only
  async rewrites() {
    if (process.env.NODE_ENV === "development") {
      return [
        {
          source: "/api/:path*",
          destination: "http://localhost:8000/:path*",
        },
      ];
    }
    return [];
  },
};

export default nextConfig;
