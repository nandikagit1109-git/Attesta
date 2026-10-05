import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiGet, apiPost } from "../lib/api";
import type { JobMatch, ShareProfile } from "../lib/types";
import TrustBadge from "../components/TrustBadge";
import AgentTrace from "../components/AgentTrace";
import { fmtDate, fmtHash } from "../lib/format";

/**
 * Guest recruiter view: the target of a share link or QR code. No login.
 * Shows exactly one published profile — statuses, skill cards with
 * confidence, on-chain proof and the agent trace. No file downloads, no
 * way to enumerate any other profile.
 */
export default function ShareView() {
  const { shareToken } = useParams();
  const [profile, setProfile] = useState<ShareProfile | null>(null);
  const [error, setError] = useState("");
  const [jd, setJd] = useState("");
  const [match, setMatch] = useState<JobMatch | null>(null);
  const [matchBusy, setMatchBusy] = useState(false);
  const [matchError, setMatchError] = useState("");

  useEffect(() => {
    if (!shareToken) return;
    setProfile(null);
    setError("");
    apiGet<ShareProfile>(`/api/share/${shareToken}`)
      .then(setProfile)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [shareToken]);

  async function runMatch() {
    if (!shareToken) return;
    setMatchBusy(true);
    setMatchError("");
    try {
      setMatch(
        await apiPost<JobMatch>(`/api/share/${shareToken}/job-match`, {
          job_description: jd,
          role_hint: null,
        }),
      );
    } catch (e) {
      setMatchError(e instanceof Error ? e.message : String(e));
    } finally {
      setMatchBusy(false);
    }
  }

  if (error) {
    return (
      <div>
        <h1 className="font-display text-3xl font-semibold">Shared profile</h1>
        <p className="mt-3 text-sm text-rust">{error}</p>
        <p className="mt-3 text-sm">
          Ask the student for a fresh link, or{" "}
          <Link to="/verify" className="underline underline-offset-4">
            verify a file directly
          </Link>{" "}
          — that never needs an account either.
        </p>
      </div>
    );
  }
  if (!profile) return <p className="text-sm">Loading</p>;

  const name = profile.student.full_name || "This student";

  return (
    <div>
      <div className="flex flex-wrap items-baseline justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-wide">Shared profile · you are a guest, no login needed</p>
          <h1 className="font-display text-3xl font-semibold">{name}</h1>
          {profile.student.headline && <p className="mt-1 text-sm">{profile.student.headline}</p>}
        </div>
        <p className="font-mono text-xs mono-break">{profile.student.wallet_address}</p>
      </div>

      <p className="mt-4 text-sm border border-ink bg-surface px-3 py-2 max-w-3xl">
        {profile.summary || "No summary yet."}
      </p>

      <div className="mt-8 grid grid-cols-1 lg:grid-cols-12 gap-8">
        <section className="lg:col-span-5">
          <h2 className="text-xs uppercase tracking-wide border-b border-ink pb-1">Skills</h2>
          <ul className="mt-3 flex flex-wrap gap-2">
            {profile.skills.length === 0 && <li className="text-sm">None extracted yet.</li>}
            {profile.skills.map((s) => (
              <li
                key={s.id}
                className={`text-xs px-2 py-1 border ${s.verified ? "border-[2.5px] border-double border-ink" : "border border-dashed border-ink"}`}
              >
                {s.name} · {s.verified ? "verified" : "unverified"}
                {s.confidence !== null && s.confidence !== undefined && (
                  <span className="font-mono"> · {Math.round(s.confidence * 100)}%</span>
                )}
              </li>
            ))}
          </ul>

          {profile.projects.length > 0 && (
            <>
              <h2 className="mt-6 text-xs uppercase tracking-wide border-b border-ink pb-1">Projects</h2>
              <ul className="mt-3 space-y-2">
                {profile.projects.map((p) => (
                  <li key={p.id} className="border border-ink px-3 py-2">
                    <p className="font-display">{p.title}</p>
                    {p.description && <p className="text-xs mt-1">{p.description}</p>}
                    <p className="font-mono text-[11px] mt-1">{p.skills.join(", ")}</p>
                  </li>
                ))}
              </ul>
            </>
          )}

          <div className="mt-8 border border-ink p-4">
            <h2 className="font-display text-xl">Match a job description</h2>
            <p className="mt-1 text-xs">
              The score counts issuer-verified skills only. Unverified matches are listed
              separately and never inflate the score.
            </p>
            <textarea
              rows={5}
              value={jd}
              onChange={(e) => setJd(e.target.value)}
              maxLength={8000}
              placeholder="Paste the posting here (min 10 characters)..."
              className="mt-3 w-full"
            />
            <button
              onClick={runMatch}
              disabled={matchBusy || jd.trim().length < 10}
              className="mt-3 bg-rust text-paper px-5 py-2 text-sm disabled:opacity-50"
            >
              Compute match score
            </button>
            {matchBusy && <p className="mt-3 text-sm">Loading</p>}
            {matchError && <p className="mt-3 text-sm text-rust">{matchError}</p>}
            {match && (
              <div className="mt-4 border border-ink">
                <div className="border-b border-ink px-3 py-2 flex items-baseline gap-4">
                  <p className="font-display text-3xl font-semibold">{match.score}/100</p>
                  <p className="text-xs">{match.reasoning}</p>
                </div>
                <div className="grid grid-cols-3 divide-x divide-ink text-xs">
                  <div className="px-3 py-2">
                    <p className="uppercase tracking-wide">Verified matches</p>
                    <ul className="mt-1 font-mono">
                      {match.matched.length === 0 && <li>None.</li>}
                      {match.matched.map((m) => <li key={m.skill_id}>{m.skill_id}</li>)}
                    </ul>
                  </div>
                  <div className="px-3 py-2 bg-surface">
                    <p className="uppercase tracking-wide">Unverified (not counted)</p>
                    <ul className="mt-1 font-mono">
                      {match.unverified.length === 0 && <li>None.</li>}
                      {match.unverified.map((m) => <li key={m.skill_id}>{m.skill_id}</li>)}
                    </ul>
                  </div>
                  <div className="px-3 py-2">
                    <p className="uppercase tracking-wide">Missing</p>
                    <ul className="mt-1 font-mono">
                      {match.missing.length === 0 && <li>None.</li>}
                      {match.missing.map((m) => <li key={m.skill_id}>{m.skill_id}</li>)}
                    </ul>
                  </div>
                </div>
              </div>
            )}
          </div>
        </section>

        <section className="lg:col-span-7 lg:border-l border-ink lg:pl-8">
          <h2 className="text-xs uppercase tracking-wide border-b border-ink pb-1">
            Credentials with on-chain proof
          </h2>
          {profile.credentials.length === 0 ? (
            <p className="mt-3 text-sm border border-ink bg-surface px-4 py-3">
              No confirmed credentials yet.
            </p>
          ) : (
            <ul className="mt-3 space-y-4">
              {profile.credentials.map((c) => (
                <li key={c.id} className="border border-ink">
                  <div className="px-4 py-3 flex flex-wrap items-center gap-3 border-b border-ink">
                    <TrustBadge state={c.status} />
                    <span className="font-display">{c.title}</span>
                    <span className="text-xs">{c.issuer_org}</span>
                    <Link to={c.receipt_path} className="ml-auto text-xs border border-ink px-2 py-1">
                      Open receipt
                    </Link>
                  </div>
                  <dl className="px-4 py-3 text-xs grid grid-cols-1 md:grid-cols-2 gap-2">
                    <div>
                      <dt className="uppercase tracking-wide">Document hash</dt>
                      <dd className="font-mono mono-break mt-0.5">{fmtHash(c.doc_hash, 20)}</dd>
                    </div>
                    <div>
                      <dt className="uppercase tracking-wide">Issuer address</dt>
                      <dd className="font-mono mono-break mt-0.5">{c.issuer_address || "unknown"}</dd>
                    </div>
                    <div>
                      <dt className="uppercase tracking-wide">Transaction hash</dt>
                      <dd className="font-mono mono-break mt-0.5">{fmtHash(c.tx_hash, 20)}</dd>
                    </div>
                    <div>
                      <dt className="uppercase tracking-wide">Block · issued</dt>
                      <dd className="font-mono mt-0.5">
                        {c.block_number} · {fmtDate(c.issued_at)}
                      </dd>
                    </div>
                  </dl>
                  {c.revoked && (
                    <p className="px-4 pb-3 text-xs text-rust">
                      Revoked {fmtDate(c.revoked_at)}: {c.revoke_reason}
                    </p>
                  )}
                  <details className="border-t border-ink px-4 py-2">
                    <summary className="text-xs cursor-pointer uppercase tracking-wide">
                      Agent trace ({c.agent_runs.length} runs)
                    </summary>
                    <div className="mt-2">
                      <AgentTrace runs={c.agent_runs} />
                    </div>
                  </details>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-4 text-xs">
            Files are never downloadable here. Want to check a document yourself?{" "}
            <Link to="/verify" className="underline underline-offset-4">
              Verify any file
            </Link>{" "}
            hashes it in your own browser and asks the chain, not us.
          </p>
        </section>
      </div>
    </div>
  );
}
