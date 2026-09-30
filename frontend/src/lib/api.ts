/** Thin API client. Uses relative /api (Vite dev proxy) unless VITE_API_BASE is set. */
const BASE: string = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";

export class ApiError extends Error {
  readonly code: string;
  readonly details: unknown;
  constructor(code: string, message: string, details: unknown) {
    super(message);
    this.code = code;
    this.details = details;
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!resp.ok) {
    let code = "UNKNOWN";
    let message = `HTTP ${resp.status}`;
    let details: unknown = null;
    try {
      const body = (await resp.json()) as { error?: { code: string; message: string; details?: unknown } };
      if (body?.error) {
        code = body.error.code;
        message = body.error.message;
        details = body.error.details ?? null;
      }
    } catch {
      // non-JSON error body — keep defaults
    }
    throw new ApiError(code, message, details);
  }
  return (await resp.json()) as T;
}

export interface Health {
  status: string;
  service: string;
  version: string;
  time: string;
  trust_states: string[];
  llm_mode: string;
}

export const getHealth = () => apiFetch<Health>("/api/health");
