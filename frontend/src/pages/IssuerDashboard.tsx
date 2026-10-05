import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { apiGet, apiPost, apiUpload } from "../lib/api";
import type { BulkRow, Credential, Evidence } from "../lib/types";
import TrustBadge from "../components/TrustBadge";
import { fmtDate, fmtHash } from "../lib/format";

interface Queue {
  pending: Evidence[];
  issued: Credential[];
}

/** Issuer desk: approve evidence, bulk-issue from CSV, revoke with a reason. */
export default function IssuerDashboard() {
  const [queue, setQueue] = useState<Queue | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [revokeFor, setRevokeFor] = useState<string>("");
  const [reason, setReason] = useState("");
  const [bulkRows, setBulkRows] = useState<BulkRow[] | null>(null);
  const csvRef = useRef<HTMLInputElement>(null);

  const reload = useCallback(async () => {
    try {
      setQueue(await apiGet<Queue>("/api/credentials/queue"));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  async function issue(evidenceId: string) {
    setBusy(true);
    setError("");
    try {
      await apiPost("/api/credentials/issue", { evidence_id: evidenceId });
      setNotice("Approved. The hash is anchored on-chain and the integrity agent re-checked it.");
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function revoke(credentialId: string) {
    if (!reason.trim()) {
      setError("A revoke reason is required.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await apiPost(`/api/credentials/${credentialId}/revoke`, { reason: reason.trim() });
      setNotice(`Revoked. The reason and timestamp are now visible on the public verify page.`);
      setRevokeFor("");
      setReason("");
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function bulk(file: File | undefined) {
    if (!file) return;
    setBusy(true);
    setError("");
    setBulkRows(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const out = await apiUpload<{ results: BulkRow[] }>("/api/credentials/bulk", form);
      setBulkRows(out.results);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <div className="flex flex-wrap items-baseline justify-between gap-4">
        <h1 className="font-display text-3xl font-semibold">Issuer desk</h1>
        <span className="text-xs">Sample data · Springfield College</span>
      </div>
      {error && <p className="mt-3 text-sm text-rust">{error}</p>}
      {notice && <p className="mt-3 text-sm">{notice}</p>}
      {busy && <p className="mt-3 text-sm">Working. Loading</p>}

      <div className="mt-6 grid grid-cols-1 lg:grid-cols-12 gap-8">
        <section className="lg:col-span-5">
          <h2 className="text-xs uppercase tracking-wide border-b border-ink pb-1">
            Awaiting confirmation (student approved the skills)
          </h2>
          {!queue ? (
            <p className="mt-3 text-sm">Loading</p>
          ) : queue.pending.length === 0 ? (
            <p className="mt-3 text-sm border border-ink bg-surface px-4 py-3">
              Nothing in the queue. Evidence lands here once the student approves the
              extracted skills and requests confirmation.
            </p>
          ) : (
            <ul className="mt-3 border border-ink divide-y divide-ink">
              {queue.pending.map((e) => (
                <li key={e.id} className="px-4 py-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <TrustBadge state={e.trust_state} />
                    <Link to={`/evidence/${e.id}`} className="font-display underline underline-offset-4">
                      {e.title || e.file_name}
                    </Link>
                    <span className="text-xs">
                      {e.student?.full_name ?? "student"} · {fmtDate(e.created_at)}
                    </span>
                  </div>
                  <p className="mt-1 text-xs">
                    Read as: {e.extracted.title || e.file_name} · issuer {e.extracted.issuer || "unknown"} ·{" "}
                    {(e.extracted.skills ?? []).length} skill(s) approved by the student
                  </p>
                  <button
                    onClick={() => issue(e.id)}
                    disabled={busy}
                    className="mt-2 bg-rust text-paper px-4 py-1 text-xs"
                  >
                    Approve and anchor on-chain
                  </button>
                </li>
              ))}
            </ul>
          )}

          <h2 className="mt-8 text-xs uppercase tracking-wide border-b border-ink pb-1">
            CSV bulk issuance
          </h2>
          <p className="mt-2 text-xs">
            Columns: student_email, title, file_name. Missing students are created with wallets and
            real sample PDFs are issued on-chain.
          </p>
          <input
            ref={csvRef}
            type="file"
            accept=".csv"
            onChange={(e) => bulk(e.target.files?.[0])}
            className="mt-2 w-full border-0 p-0 text-sm file:mr-3 file:border file:border-ink file:bg-paper file:px-3 file:py-1 file:text-ink file:text-xs"
          />
          {bulkRows && (
            <table className="mt-3 w-full border border-ink text-xs">
              <thead>
                <tr className="border-b border-ink bg-surface">
                  <th className="text-left px-2 py-1">Student email</th>
                  <th className="text-left px-2 py-1">Status</th>
                  <th className="text-left px-2 py-1">Tx</th>
                </tr>
              </thead>
              <tbody>
                {bulkRows.map((r, i) => (
                  <tr key={i} className="border-b border-ink last:border-b-0">
                    <td className="px-2 py-1 font-mono">{r.student_email}</td>
                    <td className="px-2 py-1">{r.status === "issued" ? "issued" : `error: ${r.error}`}</td>
                    <td className="px-2 py-1 font-mono">{r.tx_hash ? fmtHash(r.tx_hash, 8) : ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        <section className="lg:col-span-7 lg:border-l border-ink lg:pl-8">
          <h2 className="text-xs uppercase tracking-wide border-b border-ink pb-1">
            Issued by you
          </h2>
          {!queue || queue.issued.length === 0 ? (
            <p className="mt-3 text-sm border border-ink bg-surface px-4 py-3">
              Nothing issued yet.
            </p>
          ) : (
            <ul className="mt-3 border border-ink divide-y divide-ink">
              {queue.issued.map((c) => (
                <li key={c.id} className="px-4 py-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <TrustBadge state={c.revoked ? "Revoked" : "Verified"} />
                    <Link
                      to={`/receipt/${c.id}?hash=${c.doc_hash}`}
                      className="text-sm underline underline-offset-4"
                    >
                      credential {fmtHash(c.id, 8)}
                    </Link>
                    <span className="font-mono text-xs">
                      block {c.block_number} · tx {fmtHash(c.tx_hash, 8)} · {fmtDate(c.issued_at)}
                    </span>
                  </div>
                  {c.revoked ? (
                    <p className="mt-1 text-xs">
                      Revoked {fmtDate(c.revoked_at)}: {c.revoke_reason}
                    </p>
                  ) : revokeFor === c.id ? (
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      <input
                        placeholder="Reason (required)"
                        value={reason}
                        onChange={(e) => setReason(e.target.value)}
                        className="flex-1 min-w-48"
                        maxLength={300}
                      />
                      <button onClick={() => revoke(c.id)} className="border border-rust text-rust px-3 py-1 text-xs">
                        Confirm revoke
                      </button>
                      <button onClick={() => setRevokeFor("")} className="border border-ink px-3 py-1 text-xs">
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => setRevokeFor(c.id)}
                      className="mt-2 border border-ink px-3 py-1 text-xs"
                    >
                      Revoke
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
