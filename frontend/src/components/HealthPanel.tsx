import { useEffect, useState } from "react";
import { getHealth, type Health } from "../lib/api";

/** Live backend status: health, LLM mode, and the three trust states. */
export default function HealthPanel() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch((e: Error) => setError(e.message));
  }, []);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Backend status
        </h2>
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${
            health
              ? "bg-emerald-100 text-emerald-800 ring-emerald-300"
              : "bg-rose-100 text-rose-800 ring-rose-300"
          }`}
        >
          <span
            className={`h-1.5 w-1.5 rounded-full ${health ? "bg-emerald-500" : "bg-rose-500"}`}
            aria-hidden
          />
          {health ? "online" : "offline"}
        </span>
      </div>

      {error && <p className="mt-3 text-sm text-rose-700">Cannot reach API: {error}</p>}

      {health && (
        <dl className="mt-4 grid grid-cols-2 gap-4 text-sm">
          <div>
            <dt className="text-slate-500">Service</dt>
            <dd className="font-medium">
              {health.service} v{health.version}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500">LLM mode</dt>
            <dd className="font-medium">
              {health.llm_mode === "llm"
                ? "LLM configured"
                : "Deterministic fallback (no API key needed)"}
            </dd>
          </div>
          <div className="col-span-2">
            <dt className="text-slate-500">Trust states (frozen vocabulary)</dt>
            <dd className="mt-1 flex flex-wrap gap-2">
              {health.trust_states.map((s) => (
                <span
                  key={s}
                  className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700 ring-1 ring-slate-200"
                >
                  {s}
                </span>
              ))}
            </dd>
          </div>
        </dl>
      )}
    </div>
  );
}
