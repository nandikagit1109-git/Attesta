import { useEffect, useState } from "react";
import { apiGet } from "../lib/api";
import type { AuditEvent } from "../lib/types";
import { fmtHash } from "../lib/format";

/**
 * Feature 6: the audit log is public and read-only. It shows only what the
 * chain proves — registry events plus off-chain tamper detections, labeled —
 * with hashes, addresses, event types, transaction hashes and timestamps.
 * No names, no emails, no file names.
 */
export default function AuditPage() {
  const [rows, setRows] = useState<AuditEvent[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiGet<AuditEvent[]>("/api/audit?limit=200")
      .then(setRows)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  return (
    <div>
      <h1 className="font-display text-3xl font-semibold">Audit log</h1>
      <p className="mt-2 text-sm">
        Public and read-only. Registry events are read from the contract's event logs; tamper
        detections never touch the chain (it is immutable), so they are labeled{" "}
        <span className="border border-ink px-1 py-0.5 text-[11px] font-mono">off-chain</span>.
        Hashes, addresses, event types, transaction hashes, timestamps — nothing else.
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
              <th className="px-2 py-1">Event</th>
              <th className="px-2 py-1">Source</th>
              <th className="px-2 py-1">Document hash</th>
              <th className="px-2 py-1">Issuer address</th>
              <th className="px-2 py-1">Transaction</th>
              <th className="px-2 py-1">Detail</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.key} className="border-b border-ink last:border-b-0 align-top">
                <td className="px-2 py-1 whitespace-nowrap">{r.at ? r.at.replace("T", " ").slice(0, 19) : "unknown"}</td>
                <td className="px-2 py-1 font-mono">{r.event}</td>
                <td className="px-2 py-1">{r.source}</td>
                <td className="px-2 py-1 font-mono mono-break">
                  {r.doc_hash ? fmtHash(r.doc_hash, 12) : ""}
                </td>
                <td className="px-2 py-1 font-mono mono-break">
                  {r.issuer_address ? fmtHash(r.issuer_address, 10) : ""}
                </td>
                <td className="px-2 py-1 font-mono mono-break">
                  {r.tx_hash ? fmtHash(r.tx_hash, 12) : ""}
                  {r.block_number !== null ? ` · block ${r.block_number}` : ""}
                </td>
                <td className="px-2 py-1">
                  {r.event === "revoked" && r.reason ? `reason: ${r.reason}` : ""}
                  {r.event === "tamper-detected" && r.reason
                    ? `original ${fmtHash(r.reason, 10)}`
                    : ""}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
