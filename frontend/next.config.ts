import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Allow a production build while `next dev` is using `.next`.
  distDir: process.env.NEXT_DIST_DIR || ".next",
};

export default nextConfig;
