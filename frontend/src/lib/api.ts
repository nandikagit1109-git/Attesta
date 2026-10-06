/**
 * Thin fetch wrapper around the Attesta API.
 * - Base URL comes from VITE_API_BASE (empty = same origin / Vite proxy).
 * - If that endpoint cannot be reached at the transport level, the client
 *   transparently fails over to VITE_API_FALLBACK_BASE (Render backend).
 * - JWT travels in the Authorization header, stored in localStorage.
 * - Errors surface the standard envelope {error:{code,message,details}}.
 */

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";
// Public demo URL (also in render.yaml/README); overridable via env var.
const FALLBACK =
  (import.meta.env.VITE_API_FALLBACK_BASE as string | undefined) ??
  "https://trustpass-api-vxrh.onrender.com";

/** Candidate API bases in priority order, deduplicated. Empty BASE means
 * same-origin (Vite dev proxy or a co-hosted deploy) — no failover there. */
const CANDIDATES: string[] =
  BASE === "" ? [] : [...new Set([BASE, FALLBACK].filter((b) => b !== ""))];

/** Sticky index into CANDIDATES: after a failover we stay on what works. */
let preferred = 0;

/** Per-attempt transport timeout; also bounds how long a dead path can hang a call. */
const ATTEMPT_TIMEOUT_MS = 30_000;

/** Server-side hiccups worth retrying (e.g. Render free tier waking up). */
const RETRYABLE_STATUSES = new Set([502, 503, 504]);

/** Full URL for browser-navigated downloads (not fetch calls). */
export function apiUrl(path: string): string {
  return `${CANDIDATES[preferred] ?? BASE}${path}`;
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

function errorMessage(): string {
  const tried = CANDIDATES.length > 1 ? "primary and fallback endpoints" : "the Attesta API";
  return `Cannot reach the Attesta API (${tried}). Is the backend running?`;
}

/** One fetch attempt against one base. Throws ApiError(0) on transport failure. */
async function attempt<T>(base: string, path: string, init: RequestInit): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let resp: Response;
  try {
    resp = await fetch(`${base}${path}`, {
      ...init,
      headers,
      signal: AbortSignal.timeout(ATTEMPT_TIMEOUT_MS),
    });
  } catch {
    throw new ApiError(0, "NETWORK", errorMessage());
  }

  const text = await resp.text();
  let data: unknown = null;
  try {
    data = text ? (JSON.parse(text) as unknown) : null;
  } catch {
    // Non-JSON body (e.g. proxy error page): treat like a retryable transport failure.
    if (!resp.ok) throw new ApiError(resp.status, "NETWORK", errorMessage());
    throw new ApiError(resp.status, "ERROR", "Unexpected non-JSON response from the API.");
  }
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

async function request<T>(path: string, init: RequestInit): Promise<T> {
  if (CANDIDATES.length === 0) return attempt<T>("", path, init);

  // Round-robin from the preferred base; a second round gives cold starts and
  // transient path flakes one more chance before we surface the error.
  const order = [...CANDIDATES.slice(preferred), ...CANDIDATES.slice(0, preferred)];
  let lastError = new ApiError(0, "NETWORK", errorMessage());
  const rounds = 2;

  for (let round = 0; round < rounds; round++) {
    for (const base of order) {
      try {
        const data = await attempt<T>(base, path, init);
        preferred = Math.max(CANDIDATES.indexOf(base), 0);
        return data;
      } catch (err) {
        lastError =
          err instanceof ApiError ? err : new ApiError(0, "NETWORK", errorMessage());
        // A definitive HTTP answer (auth, validation, not-found) is final:
        // fail over only on transport failures and retryable server errors.
        if (lastError.status !== 0 && !RETRYABLE_STATUSES.has(lastError.status)) {
          throw lastError;
        }
      }
    }
  }
  throw lastError;
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
