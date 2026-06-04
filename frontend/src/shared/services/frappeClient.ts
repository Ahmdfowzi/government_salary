// Thin REST client for the Frappe backend.
// Responsibility: transport only. No payroll math happens here or anywhere in
// the frontend — calculations are backend (Python) only.

const BASE_URL =
  process.env.NEXT_PUBLIC_FRAPPE_BASE_URL ?? "http://localhost:8000";

type Query = Record<string, string | number | undefined>;

function buildUrl(path: string, query?: Query): string {
  const url = new URL(path, BASE_URL);
  if (query) {
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined) url.searchParams.set(k, String(v));
    }
  }
  return url.toString();
}

async function request<T>(path: string, init?: RequestInit, query?: Query): Promise<T> {
  const res = await fetch(buildUrl(path, query), {
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    credentials: "include",
    ...init,
  });
  if (!res.ok) {
    throw new Error(`Frappe request failed: ${res.status} ${res.statusText}`);
  }
  const json = await res.json();
  return (json.data ?? json.message ?? json) as T;
}

/** List documents of a DocType. */
export function getList<T>(doctype: string, query?: Query): Promise<T[]> {
  return request<T[]>(`/api/resource/${encodeURIComponent(doctype)}`, undefined, query);
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
