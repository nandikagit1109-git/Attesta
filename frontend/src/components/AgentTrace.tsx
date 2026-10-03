import type { AgentRun } from "../lib/types";

/**
 * Agent Trace panel (feature 2): every agent run as a step with input
 * summary, output, confidence, flags, duration and whether the deterministic
 * fallback logic was used.
 */
export default function AgentTrace({ runs }: { runs: AgentRun[] }) {
  if (!runs.length) {
    return <p className="text-sm">No agent runs recorded for this evidence yet.</p>;
  }
  return (
    <ol className="border border-ink divide-y divide-ink">
      {runs.map((run, i) => (
        <li key={run.id} className="px-4 py-3">
          <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
            <span className="font-mono text-xs">
              Step {i + 1} · {run.agent}
            </span>
            <span className="text-xs">confidence {Math.round(run.confidence * 100)}%</span>
            <span className="text-xs">{run.duration_ms} ms</span>
            <span className="text-xs">{run.used_fallback ? "deterministic fallback" : "LLM"}</span>
          </div>
          <p className="text-sm mt-1">{run.input_summary}</p>
          <pre className="mt-2 border border-ink bg-surface px-3 py-2 font-mono text-[11px] leading-4 overflow-x-auto whitespace-pre-wrap">
            {JSON.stringify(run.output, null, 2)}
          </pre>
          {run.flags.length > 0 && (
            <p className="mt-2 text-xs">
              Flags:{" "}
              {run.flags.map((f) => (
                <span key={f} className="border border-ink px-1 py-0.5 font-mono text-[11px] mr-1 inline-block">
                  {f}
                </span>
              ))}
            </p>
          )}
        </li>
      ))}
    </ol>
  );
}
