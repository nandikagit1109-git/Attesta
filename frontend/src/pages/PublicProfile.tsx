import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiGet } from "../lib/api";
import type { PublicProfile as ProfileData } from "../lib/types";
import TrustBadge from "../components/TrustBadge";
import { fmtHash } from "../lib/format";

/** Feature 9: the public profile renders only the fields the student opted in. */
export default function PublicProfilePage() {
  const { userId } = useParams();
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!userId) return;
    apiGet<ProfileData>(`/api/profiles/${userId}`)
      .then(setProfile)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [userId]);

  if (error) return <p className="text-sm text-rust">{error}</p>;
  if (!profile) return <p className="text-sm">Loading</p>;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
      <section className="lg:col-span-5 lg:border-r border-ink lg:pr-8">
        <p className="text-xs uppercase tracking-wide">Public profile</p>
        <h1 className="font-display text-3xl font-semibold">{profile.full_name ?? "Private name"}</h1>
        {profile.org_name && <p className="mt-1 text-sm">{profile.org_name}</p>}
        {profile.headline !== undefined && profile.headline !== "" && (
          <p className="mt-2 text-sm">{profile.headline}</p>
        )}
        <p className="mt-4 text-xs uppercase tracking-wide">Wallet</p>
        <p className="font-mono text-xs mono-break">{profile.wallet_address || "not generated"}</p>
        {profile.email && (
          <>
            <p className="mt-3 text-xs uppercase tracking-wide">Email</p>
            <p className="font-mono text-xs">{profile.email}</p>
          </>
        )}
        <p className="mt-4 text-xs border border-ink bg-surface px-3 py-2">
          {profile.summary || "No summary yet."}
        </p>
        <p className="mt-2 text-xs">
          This page shows only the fields the owner made public. Sample data is labeled as such.
        </p>
      </section>

      <section className="lg:col-span-7">
        {profile.skills && (
          <>
            <h2 className="text-xs uppercase tracking-wide border-b border-ink pb-1">Skills</h2>
            <div className="mt-2">
              <p className="text-xs uppercase tracking-wide mt-3">Verified</p>
              <ul className="mt-1 flex flex-wrap gap-2">
                {profile.skills.verified.length === 0 && <li className="text-sm">None public.</li>}
                {profile.skills.verified.map((s) => (
                  <li key={s} className="text-xs px-2 py-1 border-[2.5px] border-double border-ink">
                    {s} · verified
                  </li>
                ))}
              </ul>
              <p className="text-xs uppercase tracking-wide mt-3">Unverified</p>
              <ul className="mt-1 flex flex-wrap gap-2">
                {profile.skills.unverified.length === 0 && <li className="text-sm">None public.</li>}
                {profile.skills.unverified.map((s) => (
                  <li key={s} className="text-xs px-2 py-1 border border-dashed border-ink">
                    {s} · unverified
                  </li>
                ))}
              </ul>
            </div>
          </>
        )}

        {profile.credentials && (
          <>
            <h2 className="mt-6 text-xs uppercase tracking-wide border-b border-ink pb-1">
              Credentials
            </h2>
            <ul className="mt-2 border border-ink divide-y divide-ink">
              {profile.credentials.length === 0 && <li className="px-3 py-2 text-sm">None public.</li>}
              {profile.credentials.map((c) => (
                <li key={c.id} className="px-3 py-2 flex flex-wrap items-center gap-3">
                  <TrustBadge state={c.trust_state} />
                  <span className="text-sm">{c.title}</span>
                  <span className="font-mono text-xs">{fmtHash(c.id, 8)}</span>
                </li>
              ))}
            </ul>
          </>
        )}

        {profile.projects && (
          <>
            <h2 className="mt-6 text-xs uppercase tracking-wide border-b border-ink pb-1">Projects</h2>
            <ul className="mt-2 space-y-2">
              {profile.projects.length === 0 && <li className="text-sm">None public.</li>}
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

        {profile.role === "student" && (
          <p className="mt-6 text-xs">
            Want proof? Open{" "}
            <Link to="/verify" className="underline underline-offset-4">
              Verify any file
            </Link>{" "}
            and check any of these documents yourself, on-chain.
          </p>
        )}
      </section>
    </div>
  );
}
