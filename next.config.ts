import type { NextConfig } from "next";

const isDev = process.env.NODE_ENV !== "production";
const apiProxyTarget =
  process.env.NEXT_PUBLIC_API_PROXY_TARGET || "http://localhost:8080";

const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: {
    unoptimized: true,
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async rewrites() {
    if (!isDev) return [];
    return [
      { source: "/api/:path*", destination: `${apiProxyTarget}/api/:path*` },
      {
        source: "/pubsub/:path*",
        destination: `${apiProxyTarget}/pubsub/:path*`,
      },
    ];
  },
};

export default nextConfig;
