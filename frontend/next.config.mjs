/** @type {import('next').NextConfig} */

// The Frappe backend the dev/prod server proxies API calls to. Override with the
// FRAPPE_PROXY_TARGET env var. Default targets the bench site host so Frappe
// resolves the correct site (host-based routing) — `localhost:8000` would 404.
const FRAPPE_TARGET =
  process.env.FRAPPE_PROXY_TARGET ?? "http://payroll.localhost:8000";

const nextConfig = {
  reactStrictMode: true,
  // Same-origin proxy: the browser calls the Next app's own origin (/api/...),
  // and the server forwards to Frappe. This removes the cross-origin CORS block
  // and the host-routing 404 that surfaced as "Load failed" in the UI. The
  // frontend uses a relative API base (see frappeClient) so it rides this proxy.
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${FRAPPE_TARGET}/api/:path*` },
      { source: "/files/:path*", destination: `${FRAPPE_TARGET}/files/:path*` },
      { source: "/private/files/:path*", destination: `${FRAPPE_TARGET}/private/files/:path*` },
    ];
  },
};
export default nextConfig;
