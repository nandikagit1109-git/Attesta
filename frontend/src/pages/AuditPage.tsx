import { useEffect, useState } from "react";
import { apiGet } from "../lib/api";
import type { AuditEntry } from "../lib/types";
import { fmtDate } from "../lib/format";

/** Feature 10: the audit trail. Students see their own rows; staff see all. */
export default function AuditPage() {
  const [rows, setRows] = useState<AuditEntry[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiGet<AuditEntry[]>("/api/audit?limit=200")
      .then(setRows)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  return (
    <div>
      <h1 className="font-display text-3xl font-semibold">Audit log</h1>
      <p className="mt-2 text-sm">
        Every issue, revoke, verify and agent run, in order. Nothing is edited after the fact.
      </p>
      {error && <p className="mt-3 text-sm text-rust">{error}</p>}
      {!rows ? (
        <p className="mt-4 text-sm">Loading</p>
      ) : rows.length === 0 ? (
        <p className="mt-4 text-sm border border-ink bg-surface px-4 py-3">No entries yet.</p>
      ) : (
        <table className="mt-4 w-full border border-ink text-xs">
          <thead>
            <tr className="border-b border-ink bg-surface text-left">
              <th className="px-2 py-1">When</th>
              <th className="px-2 py-1">Actor</th>
              <th className="px-2 py-1">Action</th>
              <th className="px-2 py-1">Object</th>
              <th className="px-2 py-1">Detail</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-b border-ink last:border-b-0 align-top">
                <td className="px-2 py-1 whitespace-nowrap">{fmtDate(r.created_at)}</td>
                <td className="px-2 py-1">{r.actor_role || "anonymous"}</td>
                <td className="px-2 py-1 font-mono">{r.action}</td>
                <td className="px-2 py-1">
                  {r.object_type}
                  {r.object_id ? ` ${r.object_id.slice(0, 8)}...` : ""}
                </td>
                <td className="px-2 py-1 font-mono mono-break">
                  {Object.keys(r.detail).length ? JSON.stringify(r.detail) : ""}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
