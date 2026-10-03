import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiGet, apiPost } from "../lib/api";
import type { DirectoryEntry, JobMatch, RolesResponse } from "../lib/types";

/** Recruiter search and job match (feature 4): score from verified skills only. */
export default function RecruiterPage() {
  const [candidates, setCandidates] = useState<DirectoryEntry[]>([]);
  const [selected, setSelected] = useState<DirectoryEntry | null>(null);
  const [roles, setRoles] = useState<RolesResponse | null>(null);
  const [roleHint, setRoleHint] = useState("");
  const [jd, setJd] = useState("");
  const [match, setMatch] = useState<JobMatch | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    apiGet<DirectoryEntry[]>("/api/profiles")
      .then(setCandidates)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
    apiGet<RolesResponse>("/api/career/roles").then(setRoles).catch(() => undefined);
  }, []);

  async function runMatch() {
    if (!selected) return;
    setBusy(true);
    setError("");
    try {
      setMatch(
        await apiPost<JobMatch>("/api/career/job-match", {
          job_description: jd,
          role_hint: roleHint || null,
          candidate_id: selected.user_id,
        }),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1 className="font-display text-3xl font-semibold">Recruiter desk</h1>
      <p className="mt-2 text-sm">
        Scores come from issuer-verified skills only. Unverified matches are listed separately and
        never inflate the score. Sample data is labeled as such.
      </p>
      {error && <p className="mt-3 text-sm text-rust">{error}</p>}

      <div className="mt-6 grid grid-cols-1 lg:grid-cols-12 gap-8">
        <section className="lg:col-span-4 lg:border-r border-ink lg:pr-8">
          <h2 className="text-xs uppercase tracking-wide border-b border-ink pb-1">Candidates</h2>
          {candidates.length === 0 ? (
            <p className="mt-3 text-sm">Loading</p>
          ) : (
            <ul className="mt-3 border border-ink divide-y divide-ink">
              {candidates.map((c) => (
                <li key={c.user_id} className="px-4 py-3">
                  <button
                    className={`w-full text-left ${selected?.user_id === c.user_id ? "bg-surface" : ""}`}
                    onClick={() => {
                      setSelected(c);
                      setMatch(null);
                    }}
                  >
                    <p className="font-display text-sm">{c.full_name ?? "Private name"}</p>
                    {c.headline && <p className="text-xs mt-0.5">{c.headline}</p>}
                    {c.skills && (
                      <p className="text-xs mt-1">
                        {c.skills.verified.length} verified · {c.skills.unverified.length} unverified
                      </p>
                    )}
                  </button>
                  <Link
                    to={`/profiles/${c.user_id}`}
                    className="text-xs underline underline-offset-4 mt-1 inline-block"
                  >
                    Public profile
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="lg:col-span-8">
          {!selected ? (
            <p className="text-sm border border-ink bg-surface px-4 py-3">
              Pick a candidate on the left, then paste a job description.
            </p>
          ) : (
            <>
              <h2 className="font-display text-2xl">Match {selected.full_name ?? "candidate"} to a job</h2>
              <label htmlFor="role-hint" className="block mt-4 text-xs uppercase tracking-wide mb-1">
                Role hint (weights the taxonomy)
              </label>
              <select id="role-hint" value={roleHint} onChange={(e) => setRoleHint(e.target.value)}>
                <option value="">No hint</option>
                {roles?.roles.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.title}
                  </option>
                ))}
              </select>
              <label htmlFor="jd" className="block mt-4 text-xs uppercase tracking-wide mb-1">
                Job description (min 10 characters)
              </label>
              <textarea
                id="jd"
                rows={6}
                value={jd}
                onChange={(e) => setJd(e.target.value)}
                className="w-full"
                maxLength={8000}
                placeholder="Paste the posting here..."
              />
              <button
                onClick={runMatch}
                disabled={busy || jd.trim().length < 10}
                className="mt-3 bg-rust text-paper px-5 py-2 text-sm disabled:opacity-50"
              >
                Compute match score
              </button>
              {busy && <p className="mt-3 text-sm">Loading</p>}

              {match && (
                <div className="mt-6 border border-ink">
                  <div className="border-b border-ink px-4 py-3 flex items-baseline gap-6">
                    <div>
                      <p className="text-xs uppercase tracking-wide">Score</p>
                      <p className="font-display text-4xl font-semibold">{match.score}/100</p>
                    </div>
                    <p className="text-sm">{match.reasoning}</p>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-ink">
                    <div className="px-4 py-3">
                      <p className="text-xs uppercase tracking-wide">Verified matches</p>
                      <ul className="mt-1 text-xs space-y-1">
                        {match.matched.length === 0 && <li>None.</li>}
                        {match.matched.map((m) => (
                          <li key={m.skill_id} className="font-mono">
                            {m.skill_id}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div className="px-4 py-3 bg-surface">
                      <p className="text-xs uppercase tracking-wide">Unverified (not counted)</p>
                      <ul className="mt-1 text-xs space-y-1">
                        {match.unverified.length === 0 && <li>None.</li>}
                        {match.unverified.map((m) => (
                          <li key={m.skill_id} className="font-mono">
                            {m.skill_id}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div className="px-4 py-3">
                      <p className="text-xs uppercase tracking-wide">Missing</p>
                      <ul className="mt-1 text-xs space-y-1">
                        {match.missing.length === 0 && <li>None.</li>}
                        {match.missing.map((m) => (
                          <li key={m.skill_id} className="font-mono">
                            {m.skill_id} · {m.priority}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </section>
      </div>
    </div>
  );
}
