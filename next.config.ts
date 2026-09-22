import type { NextConfig } from "next";
import path from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = path.dirname(fileURLToPath(import.meta.url));

const nextConfig: NextConfig = {
  output: "standalone",
  outputFileTracingRoot: projectRoot,
  outputFileTracingIncludes: {
    "/download/[name]": ["./download/*.md", "./download/*.pdf"],
  },
  turbopack: {
    root: projectRoot,
  },
  reactStrictMode: false,
};

export default nextConfig;
