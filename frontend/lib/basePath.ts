// Prepends the GitHub Pages base path (e.g. "/Eye-of-Horus") to a public/
// asset URL. A no-op on every other deployment target, where the env var is
// empty. Needed anywhere an asset is loaded by a hand-built string path
// (next/link and CSS url() get this for free from Next's basePath config;
// this covers everything else, e.g. the R3F texture loader).
export function withBasePath(path: string): string {
  const base = process.env.NEXT_PUBLIC_BASE_PATH || "";
  return `${base}${path}`;
}
