import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, apiGet, apiPost } from "../lib/api";
import type { Credential } from "../lib/types";
import TrustBadge from "../components/TrustBadge";
import { fmtDate, fmtHash } from "../lib/format";

interface SeedSummary {
  verified: { credential_id: string };
  tampered: { sha256: string; credential_id: string };
}

interface TamperResult {
  credential_id: string;
  original_sha256: string;
  tampered_sha256: string;
  note: string;
}

/**
 * Demo/Admin control (revised spec role 4): owns the seed data, the
 * "Reset demo data" button and the one-click tamper. Both destructive
 * actions are refused by the API in production deployments.
 */
export default function AdminPage() {
  const [credentials, setCredentials] = useState<Credential[] | null>(null);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [tampered, setTampered] = useState<TamperResult | null>(null);

  const reload = useCallback(async () => {
    try {
      setCredentials(await apiGet<Credential[]>("/api/credentials"));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  function describe(e: unknown) {
    if (e instanceof ApiError && e.status === 403) {
      return "Disabled: demo controls are refused in production. Run the demo locally (./make demo-check or the dev server).";
    }
    return e instanceof Error ? e.message : String(e);
  }

  async function reset() {
    setBusy(true);
    setError("");
    setNotice("");
    setTampered(null);
    try {
      const seed = await apiPost<SeedSummary>("/api/demo/reset");
      setNotice(
        `Demo data reset. Verified credential ${seed.verified.credential_id.slice(0, 8)}… with a pre-staged tampered copy.`,
      );
      await reload();
    } catch (e) {
      setError(describe(e));
    } finally {
      setBusy(false);
    }
  }

  async function tamper(credentialId: string) {
    setBusy(true);
    setError("");
    setTampered(null);
    try {
      const out = await apiPost<TamperResult>(`/api/demo/tamper/${credentialId}`);
      setTampered(out);
      await reload();
    } catch (e) {
      setError(describe(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <div className="flex flex-wrap items-baseline justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-semibold">Demo admin</h1>
          <p className="mt-2 text-sm">
            Owns the sample dataset. The tamper control flips one byte of a stored copy and marks
            the credential HASH MISMATCH — the on-chain record stays untouched, and the audit log
            records an off-chain tamper-detection entry.
          </p>
        </div>
        <button onClick={reset} disabled={busy} className="bg-rust text-paper px-5 py-2 text-sm disabled:opacity-50">
          Reset demo data
        </button>
      </div>

      {error && <p className="mt-3 text-sm text-rust">{error}</p>}
      {notice && <p className="mt-3 text-sm">{notice}</p>}
      {busy && <p className="mt-3 text-sm">Working. Loading</p>}

      {tampered && (
        <div className="mt-4 border border-rust p-3 text-xs">
          <p className="font-semibold">Tampered copy created for credential {tampered.credential_id.slice(0, 8)}…</p>
          <p className="mt-1 font-mono mono-break">Original: {tampered.original_sha256}</p>
          <p className="font-mono mono-break">Tampered: {tampered.tampered_sha256}</p>
          <p className="mt-1">{tampered.note}</p>
          <Link
            to={`/receipt/${tampered.credential_id}?hash=${tampered.original_sha256}`}
            className="mt-2 inline-block underline underline-offset-4"
          >
            Open the receipt and drop the tampered copy to see the hex diff
          </Link>
        </div>
      )}

      <h2 className="mt-8 text-xs uppercase tracking-wide border-b border-ink pb-1">
        All credentials (one-click tamper)
      </h2>
      {!credentials ? (
        <p className="mt-3 text-sm">Loading</p>
      ) : credentials.length === 0 ? (
        <p className="mt-3 text-sm border border-ink bg-surface px-4 py-3">
          No credentials yet. Reset the demo data or walk the student/issuer flow.
        </p>
      ) : (
        <ul className="mt-3 border border-ink divide-y divide-ink">
          {credentials.map((c) => (
            <li key={c.id} className="px-4 py-3 flex flex-wrap items-center gap-3">
              <TrustBadge state={c.revoked ? "Revoked" : c.tx_hash ? "Verified" : "Unverified"} />
              <Link
                to={`/receipt/${c.id}?hash=${c.doc_hash}`}
                className="font-display underline underline-offset-4"
              >
                credential {fmtHash(c.id, 8)}
              </Link>
              <span className="font-mono text-xs">
                block {c.block_number} · tx {fmtHash(c.tx_hash, 8)} · {fmtDate(c.issued_at)}
              </span>
              {!c.revoked && (
                <button
                  onClick={() => tamper(c.id)}
                  disabled={busy}
                  className="ml-auto border border-rust text-rust px-3 py-1 text-xs disabled:opacity-50"
                >
                  One-click tamper
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
