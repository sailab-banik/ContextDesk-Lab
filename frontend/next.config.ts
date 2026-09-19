import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactCompiler: true,
  typedRoutes: true,
  // The Docker image runs the traced standalone server instead of shipping all
  // of node_modules.
  output: "standalone",
  // Bottom-left would sit on top of the chat composer's component toggles.
  devIndicators: { position: "bottom-right" },
};

export default nextConfig;
