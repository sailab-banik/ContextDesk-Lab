import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactCompiler: true,
  typedRoutes: true,
  // Bottom-left would sit on top of the chat composer's component toggles.
  devIndicators: { position: "bottom-right" },
};

export default nextConfig;
