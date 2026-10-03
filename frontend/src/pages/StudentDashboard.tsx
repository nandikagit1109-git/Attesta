import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiGet, apiPost, ApiError, apiUpload } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { Credential, Evidence } from "../lib/types";
import TrustBadge from "../components/TrustBadge";
import { fmtBytes, fmtDate, fmtHash } from "../lib/format";

/** Student home: upload evidence, follow its state, share receipts. */
export default function StudentDashboard() {
  const { user } = useAuth();
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [title, setTitle] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const reload = useCallback(async () => {
    try {
      const [ev, cr] = await Promise.all([
        apiGet<Evidence[]>("/api/evidence"),
        apiGet<Credential[]>("/api/credentials"),
      ]);
      setEvidence(ev);
      setCredentials(cr);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  async function upload(file: File | undefined) {
    if (!file) return;
    setError("");
    setNotice("");
    setBusy(true);
    try {
      const form = new FormData();
      form.append("file", file);
      if (title.trim()) form.append("title", title.trim());
      await apiUpload<Evidence>("/api/evidence", form);
      setNotice(`Analyzed ${file.name}. The agents' reading is AI-extracted (unverified) until the issuer confirms it.`);
      setTitle("");
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function resetDemo() {
    setError("");
    setNotice("");
    setBusy(true);
    try {
      await apiPost("/api/demo/reset");
      setNotice("Demo data reset. Sample certificates, credentials and the tampered copy are back.");
      await reload();
    } catch (e) {
      setError(
        e instanceof ApiError && e.status === 404
          ? "Demo reset arrives with the seed script (./make seed)."
          : e instanceof Error
            ? e.message
            : String(e),
      );
    } finally {
      setBusy(false);
    }
  }

  const verifiedSkills = new Set(
    evidence.flatMap((e) => (e.credential && !e.credential.revoked && e.trust_state === "Issuer-verified" ? e.skills.filter((s) => s.verified).map((s) => s.id) : [])),
  );

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
      <section className="lg:col-span-4 lg:border-r border-ink lg:pr-8">
        <h1 className="font-display text-3xl font-semibold">{user?.full_name}</h1>
        <p className="mt-1 text-sm">{user?.headline}</p>
        <p className="mt-3 text-xs uppercase tracking-wide">Your wallet (backend-generated)</p>
        <p className="font-mono text-[11px] mono-break">{user?.wallet_address}</p>

        <div className="mt-6 border border-ink bg-surface p-4">
          <h2 className="font-display text-lg">Upload evidence</h2>
          <p className="text-xs mt-1">
            PDF or image. The agents read it and map skills; an issuer then anchors the hash
            on-chain.
          </p>
          <input
            type="text"
            placeholder="Title (optional; agents suggest one)"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="mt-3 w-full"
          />
          <input
            type="file"
            accept=".pdf,.png,.jpg,.jpeg"
            onChange={(e) => upload(e.target.files?.[0])}
            disabled={busy}
            className="mt-3 w-full border-0 p-0 text-sm file:mr-3 file:border file:border-ink file:bg-paper file:px-3 file:py-1 file:text-ink file:text-xs"
          />
          {busy && <p className="mt-2 text-sm">Uploading and running agents. Loading</p>}
        </div>

        <div className="mt-6 border-t border-ink pt-4">
          <p className="text-sm">
            {verifiedSkills.size} verified skill{verifiedSkills.size === 1 ? "" : "s"} ·{" "}
            {evidence.length} evidence item{evidence.length === 1 ? "" : "s"} · {credentials.length}{" "}
            credential{credentials.length === 1 ? "" : "s"}
          </p>
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            <Link to="/graph" className="border border-ink px-3 py-1">
              Skill graph
            </Link>
            <Link to="/career" className="border border-ink px-3 py-1">
              Career gap
            </Link>
            <Link to="/profile" className="border border-ink px-3 py-1">
              Profile and privacy
            </Link>
          </div>
          <button onClick={resetDemo} disabled={busy} className="mt-4 border border-ink px-3 py-1 text-xs">
            Reset demo data
          </button>
        </div>

        {error && <p className="mt-4 text-sm text-rust">{error}</p>}
        {notice && <p className="mt-4 text-sm">{notice}</p>}
      </section>

      <section className="lg:col-span-8">
        <h2 className="font-display text-2xl">Evidence</h2>
        {evidence.length === 0 ? (
          <p className="mt-3 text-sm border border-ink bg-surface px-4 py-3">
            Nothing uploaded yet. Your first certificate appears here as AI-extracted (unverified)
            with the full agent trace.
          </p>
        ) : (
          <ul className="mt-3 border border-ink divide-y divide-ink">
            {evidence.map((e) => (
              <li key={e.id} className="px-4 py-3 flex flex-wrap items-center gap-3">
                <TrustBadge state={e.trust_state} />
                <Link to={`/evidence/${e.id}`} className="font-display underline underline-offset-4">
                  {e.title || e.file_name}
                </Link>
                <span className="text-xs">
                  {e.file_name} · {fmtBytes(e.file_size)} · {fmtDate(e.created_at)}
                </span>
                {e.credential && !e.credential.revoked && (
                  <Link
                    to={`/receipt/${e.credential.id}?hash=${e.sha256}`}
                    className="ml-auto text-xs border border-ink px-2 py-1"
                  >
                    Receipt + QR
                  </Link>
                )}
              </li>
            ))}
          </ul>
        )}

        <h2 className="font-display text-2xl mt-8">Credentials</h2>
        {credentials.length === 0 ? (
          <p className="mt-3 text-sm border border-ink bg-surface px-4 py-3">
            No credentials yet. They appear once an issuer approves evidence and the hash is
            anchored on-chain.
          </p>
        ) : (
          <ul className="mt-3 border border-ink divide-y divide-ink">
            {credentials.map((c) => (
              <li key={c.id} className="px-4 py-3">
                <div className="flex flex-wrap items-center gap-3">
                  <TrustBadge state={c.revoked ? "Revoked" : "Issuer-verified"} />
                  <Link to={`/receipt/${c.id}?hash=${c.doc_hash}`} className="text-sm underline underline-offset-4">
                    {c.issuer_org || c.issuer_name}
                  </Link>
                  <span className="font-mono text-xs">
                    block {c.block_number} · tx {fmtHash(c.tx_hash, 8)}
                  </span>
                </div>
                {c.revoked && (
                  <p className="mt-1 text-xs">
                    Revoked {fmtDate(c.revoked_at)}: {c.revoke_reason}
                  </p>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
