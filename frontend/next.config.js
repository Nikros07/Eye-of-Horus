const isGithubPages = process.env.BUILD_TARGET === "github-pages";
// Project-site GitHub Pages URLs are served from /<repo-name>/, so every
// asset and route needs that prefix baked in at build time — only for this
// target, never for a normal server deployment.
const repoBasePath = process.env.GH_PAGES_BASE_PATH || "/Eye-of-Horus";

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  agentRules: false,
  env: {
    NEXT_PUBLIC_API_BASE: process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000",
    // `basePath` below rewrites next/link, next/image, and CSS url() calls
    // automatically, but a hand-built asset URL in plain client JS (the R3F
    // texture loader) does not get it for free — code that loads a public/
    // asset by string path must prepend this itself.
    NEXT_PUBLIC_BASE_PATH: isGithubPages ? repoBasePath : "",
  },
  ...(isGithubPages
    ? {
        output: "export",
        basePath: repoBasePath,
        assetPrefix: repoBasePath,
        images: { unoptimized: true },
        trailingSlash: true,
      }
    : {}),
};

module.exports = nextConfig;
