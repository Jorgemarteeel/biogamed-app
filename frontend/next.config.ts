import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The development badge otherwise covers the compact correction on small windows.
  devIndicators: false,
  // Separate loopback origins keep the two demo accounts in independent storage.
  allowedDevOrigins: ["localhost", "127.0.0.1"],
};

export default nextConfig;
