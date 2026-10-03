import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiGet, apiPost, apiUrl } from "../lib/api";
import type { Evidence, VerifyResult } from "../lib/types";
import TrustBadge from "../components/TrustBadge";
import AgentTrace from "../components/AgentTrace";
import HashCompare from "../components/HashCompare";
import { fmtBytes, fmtDate } from "../lib/format";

/** Evidence detail: extracted fields, agent trace, on-chain proof, demo tamper. */
export default function EvidenceDetail() {
  const { evidenceId } = useParams();
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [tamper, setTamper] = useState<{ tampered_sha256: string; original_sha256: string; note: string } | null>(null);
  const [verifyResult, setVerifyResult] = useState<VerifyResult | null>(null);

  const reload = useCallback(async () => {
    if (!evidenceId) return;
    try {
      setEvidence(await apiGet<Evidence>(`/api/evidence/${evidenceId}`));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [evidenceId]);

  useEffect(() => {
    reload();
  }, [reload]);

  if (error) return <p className="text-sm text-rust">{error}</p>;
  if (!evidence) return <p className="text-sm">Loading</p>;

  const ex = evidence.extracted;
  const cred = evidence.credential;

  async function runVerify() {
    setBusy(true);
    setError("");
    try {
      const out = await apiPost<{ verification: Record<string, unknown>; evidence: Evidence }>(
        `/api/evidence/${evidenceId}/verify`,
      );
      setEvidence(out.evidence);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function doTamper() {
    setBusy(true);
    setError("");
    setVerifyResult(null);
    try {
      setTamper(await apiPost(`/api/evidence/${evidenceId}/tamper`));
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function verifyTampered() {
    if (!tamper) return;
    setBusy(true);
    setError("");
    try {
      setVerifyResult(await apiPost<VerifyResult>("/api/verify/hash", { sha256: tamper.tampered_sha256 }));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  const receiptLink = cred ? `${window.location.origin}/receipt/${cred.id}?hash=${evidence.sha256}` : "";

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
      <section className="lg:col-span-5">
        <div className="flex flex-wrap items-center gap-3">
          <TrustBadge state={evidence.trust_state} />
          <span className="text-xs">
            {evidence.file_name} · {fmtBytes(evidence.file_size)} · {fmtDate(evidence.created_at)}
          </span>
        </div>
        <h1 className="mt-3 font-display text-3xl font-semibold">{evidence.title || evidence.file_name}</h1>

        <h2 className="mt-6 text-xs uppercase tracking-wide border-b border-ink pb-1">
          What the agents read (AI-extracted, unverified)
        </h2>
        <dl className="mt-3 text-sm space-y-2">
          <Row label="Title" value={ex.title} />
          <Row label="Issuer" value={ex.issuer} />
          <Row label="Student name" value={ex.student_name} />
          <Row label="Date" value={ex.date} />
          <Row label="Credential ID" value={ex.credential_id} mono />
          <Row label="Extraction confidence" value={ex.confidence !== undefined ? `${Math.round(ex.confidence * 100)}%` : ""} />
        </dl>
        {(ex.flags?.length ?? 0) > 0 && (
          <p className="mt-3 text-xs">
            Flags:{" "}
            {ex.flags?.map((f) => (
              <span key={f} className="border border-ink px-1 py-0.5 font-mono text-[11px] mr-1 inline-block">
                {f}
              </span>
            ))}
          </p>
        )}
        {(ex.warnings?.length ?? 0) > 0 && (
          <p className="mt-2 text-xs">Warnings: {ex.warnings?.join("; ")}</p>
        )}

        <h2 className="mt-6 text-xs uppercase tracking-wide border-b border-ink pb-1">Skills</h2>
        <ul className="mt-3 flex flex-wrap gap-2">
          {evidence.skills.length === 0 && <li className="text-sm">No skills mapped yet.</li>}
          {evidence.skills.map((s) => (
            <li
              key={s.id}
              className={`text-xs px-2 py-1 border ${s.verified ? "border-[2.5px] border-double border-ink" : "border border-dashed border-ink"}`}
            >
              {s.name ?? s.id} · {s.verified ? "verified" : "unverified"}
            </li>
          ))}
        </ul>

        <div className="mt-6 flex flex-wrap gap-2">
          <a href={apiUrl(`/api/evidence/${evidence.id}/file`)} className="border border-ink px-3 py-1 text-xs" target="_blank" rel="noreferrer">
            Download file
          </a>
          <button onClick={runVerify} disabled={busy} className="border border-ink px-3 py-1 text-xs">
            Run integrity check now
          </button>
          <button onClick={doTamper} disabled={busy} className="border border-rust text-rust px-3 py-1 text-xs">
            Tamper with this file (demo)
          </button>
          {cred && (
            <button
              className="bg-rust text-paper px-3 py-1 text-xs"
              onClick={() => navigator.clipboard.writeText(receiptLink).catch(() => undefined)}
            >
              Copy receipt link
            </button>
          )}
          {cred && (
            <Link to={`/receipt/${cred.id}?hash=${evidence.sha256}`} className="border border-ink px-3 py-1 text-xs">
              Open receipt + QR
            </Link>
          )}
        </div>

        {tamper && (
          <div className="mt-4 border border-rust p-3 text-xs">
            <p>{tamper.note}</p>
            <p className="mt-1 font-mono mono-break">Tampered copy hash: {tamper.tampered_sha256}</p>
            <button onClick={verifyTampered} disabled={busy} className="mt-2 border border-ink px-3 py-1">
              Verify the tampered hash now
            </button>
            <a
              href={apiUrl(`/api/evidence/${evidence.id}/tamper-file`)}
              target="_blank"
              rel="noreferrer"
              className="ml-2 underline underline-offset-4"
            >
              Download tampered copy
            </a>
          </div>
        )}

        {verifyResult && (
          <div className="mt-4">
            <p className="text-xs uppercase tracking-wide mb-2">Public verification of the tampered copy</p>
            <VerifyInline result={verifyResult} />
          </div>
        )}

        {error && <p className="mt-4 text-sm text-rust">{error}</p>}
        {busy && <p className="mt-4 text-sm">Loading</p>}
      </section>

      <section className="lg:col-span-7 lg:border-l border-ink lg:pl-8">
        <h2 className="font-display text-2xl">On-chain proof</h2>
        {cred ? (
          <div className="mt-3">
            <dl className="text-sm grid grid-cols-1 md:grid-cols-2 gap-2">
              <Row label="Credential ID" value={cred.id} mono />
              <Row label="Chain credential #" value={String(cred.chain_credential_id)} mono />
              <Row label="Issuer" value={`${cred.issuer_org || cred.issuer_name} (${cred.issuer_id.slice(0, 8)}...)`} />
              <Row label="Recipient" value={cred.recipient_address} mono />
              <Row label="Block number" value={String(cred.block_number)} mono />
              <Row label="Issued" value={fmtDate(cred.issued_at)} />
              <Row label="Transaction hash" value={cred.tx_hash} mono />
            </dl>
            <div className="mt-4">
              <HashCompare presented={evidence.sha256} onchain={cred.doc_hash} />
            </div>
            {cred.revoked && (
              <p className="mt-3 text-sm">
                Revoked {fmtDate(cred.revoked_at)}: {cred.revoke_reason}
              </p>
            )}
          </div>
        ) : (
          <p className="mt-3 text-sm border border-ink bg-surface px-4 py-3">
            Not anchored yet. The issuer sees this evidence in the approval queue; after approval
            the SHA-256, issuer and recipient addresses, block and transaction hash appear here.
          </p>
        )}

        <h2 className="font-display text-2xl mt-8">Agent trace</h2>
        <p className="mt-1 text-xs">
          Every run: input summary, output, confidence, flags, duration, and whether the
          deterministic fallback was used.
        </p>
        <div className="mt-3">
          <AgentTrace runs={evidence.agent_runs ?? []} />
        </div>
      </section>
    </div>
  );
}

function Row({ label, value, mono }: { label: string; value?: string; mono?: boolean }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide">{label}</dt>
      <dd className={`mt-0.5 ${mono ? "font-mono text-xs mono-break" : ""}`}>{value || "not found"}</dd>
    </div>
  );
}

function VerifyInline({ result }: { result: VerifyResult }) {
  return (
    <div className="border border-ink px-3 py-2">
      <div className="flex items-center gap-3">
        <TrustBadge state={result.state} />
        <span className="text-xs">{result.reason}</span>
      </div>
      <div className="mt-2">
        <HashCompare presented={result.presented_hash} onchain={result.onchain_hash} />
      </div>
    </div>
  );
}
