/**
 * Thin fetch wrapper around the Attesta API.
 * - Base URL comes from VITE_API_BASE (empty = same origin / Vite proxy).
 * - JWT travels in the Authorization header, stored in localStorage.
 * - Errors surface the standard envelope {error:{code,message,details}}.
 */

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";

/** Full URL for browser-navigated downloads (not fetch calls). */
export function apiUrl(path: string): string {
  return `${BASE}${path}`;
}

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

const TOKEN_KEY = "attesta_token";

export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) ?? "";
}

export function setToken(token: string) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, init: RequestInit): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let resp: Response;
  try {
    resp = await fetch(`${BASE}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "NETWORK", "Cannot reach the Attesta API. Is the backend running?");
  }

  const text = await resp.text();
  const data = text ? (JSON.parse(text) as unknown) : null;
  if (!resp.ok) {
    const envelope = data as { error?: { code?: string; message?: string } } | null;
    throw new ApiError(
      resp.status,
      envelope?.error?.code ?? "ERROR",
      envelope?.error?.message ?? `Request failed with status ${resp.status}`,
    );
  }
  return data as T;
}

export function apiGet<T>(path: string): Promise<T> {
  return request<T>(path, { method: "GET" });
}

export function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

export function apiPatch<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: "PATCH", body: JSON.stringify(body) });
}

export function apiDelete<T>(path: string): Promise<T> {
  return request<T>(path, { method: "DELETE" });
}

export function apiUpload<T>(path: string, form: FormData): Promise<T> {
  return request<T>(path, { method: "POST", body: form });
}
