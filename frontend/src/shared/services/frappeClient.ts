// Thin REST client for the Frappe backend.
// Responsibility: transport only. No payroll math happens here or anywhere in
// the frontend — calculations are backend (Python) only.

// Default to a RELATIVE base ("") so requests go to the Next app's own origin and
// ride the same-origin proxy in next.config.mjs (which forwards /api to the Frappe
// site host). This avoids the cross-origin CORS block and the host-routing 404
// that previously surfaced as "Load failed". Set NEXT_PUBLIC_FRAPPE_BASE_URL to an
// absolute URL only if you deploy the frontend on the SAME origin as Frappe (or
// have Frappe CORS configured).
const BASE_URL = process.env.NEXT_PUBLIC_FRAPPE_BASE_URL ?? "";

type Query = Record<string, string | number | undefined>;

function buildUrl(path: string, query?: Query): string {
  const qs = query
    ? Object.entries(query)
        .filter(([, v]) => v !== undefined)
        .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
        .join("&")
    : "";
  const rel = qs ? `${path}?${qs}` : path;
  // Relative base -> resolve against the current origin (the proxy). Absolute base
  // (if explicitly configured) -> resolve against it.
  return BASE_URL ? new URL(rel, BASE_URL).toString() : rel;
}

// Pull a human-readable message out of a Frappe error response body. Frappe puts
// thrown messages in `_server_messages` (a JSON array of JSON strings) or in
// `exception` ("frappe.exceptions.ValidationError: <msg>"); fall back to status.
function extractError(body: string, status: number, statusText: string): string {
  try {
    const json = JSON.parse(body);
    if (typeof json._server_messages === "string") {
      const msgs = JSON.parse(json._server_messages) as string[];
      if (msgs.length) {
        const last = JSON.parse(msgs[msgs.length - 1]) as { message?: string };
        if (last.message) return last.message;
      }
    }
    if (typeof json.exception === "string" && json.exception.includes(": ")) {
      return json.exception.slice(json.exception.indexOf(": ") + 2);
    }
    if (typeof json.message === "string") return json.message;
  } catch {
    /* not JSON — fall through to the status line */
  }
  return `Frappe request failed: ${status} ${statusText}`;
}

async function request<T>(path: string, init?: RequestInit, query?: Query): Promise<T> {
  const res = await fetch(buildUrl(path, query), {
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    credentials: "include",
    ...init,
  });
  if (!res.ok) {
    throw new Error(extractError(await res.text(), res.status, res.statusText));
  }
  const json = await res.json();
  return (json.data ?? json.message ?? json) as T;
}

/** List documents of a DocType.
 *  Defaults to ALL fields and NO row cap — Frappe's /api/resource otherwise
 *  returns only `name` and caps at 20 rows, which left the UI tables empty.
 *  Pass `query` to override (e.g. specific fields, filters, order_by, limit). */
export function getList<T>(doctype: string, query?: Query): Promise<T[]> {
  return request<T[]>(`/api/resource/${encodeURIComponent(doctype)}`, undefined, {
    fields: JSON.stringify(["*"]),
    limit_page_length: 0,
    ...query,
  });
}

/** Fetch one document by name. */
export function getDoc<T>(doctype: string, name: string): Promise<T> {
  return request<T>(`/api/resource/${encodeURIComponent(doctype)}/${encodeURIComponent(name)}`);
}

/** Call a whitelisted backend method (e.g. a calculation endpoint). */
export function callMethod<T>(method: string, body?: unknown): Promise<T> {
  return request<T>(`/api/method/${method}`, {
    method: "POST",
    body: JSON.stringify(body ?? {}),
  });
}

/** Full URL to a whitelisted GET method — used for binary file downloads
 *  (the browser handles the Content-Disposition response). */
export function methodUrl(method: string, query?: Query): string {
  return buildUrl(`/api/method/${method}`, query);
}
