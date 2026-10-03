import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiGet, apiPatch } from "../lib/api";
import type { User } from "../lib/types";
import { useAuth } from "../lib/auth";

interface MyProfile {
  user: User;
  summary: string;
  facts: Record<string, unknown>;
  evidence_count: number;
}

const TOGGLES: { key: string; label: string }[] = [
  { key: "full_name", label: "Full name" },
  { key: "headline", label: "Headline" },
  { key: "email", label: "Email" },
  { key: "skills", label: "Skills (verified and unverified lists)" },
  { key: "projects", label: "Projects" },
  { key: "credentials", label: "Credentials" },
];

/** Feature 9: per-field privacy toggles; the public profile shows only opted-in fields. */
export default function ProfilePage() {
  const { user } = useAuth();
  const [profile, setProfile] = useState<MyProfile | null>(null);
  const [headline, setHeadline] = useState("");
  const [toggles, setToggles] = useState<Record<string, boolean>>({});
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    apiGet<MyProfile>("/api/profile/me")
      .then((p) => {
        setProfile(p);
        setHeadline(p.user.headline);
        setToggles(p.user.public_fields);
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  async function save() {
    setBusy(true);
    setNotice("");
    setError("");
    try {
      const updated = await apiPatch<User>("/api/profile/me", {
        headline,
        public_fields: toggles,
      });
      setToggles(updated.public_fields);
      setNotice("Saved. The public profile now reflects exactly these toggles.");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
      <section className="lg:col-span-6">
        <h1 className="font-display text-3xl font-semibold">Your profile</h1>
        {profile ? (
          <>
            <p className="mt-3 text-xs uppercase tracking-wide">Profile Agent summary (facts only)</p>
            <p className="mt-1 text-sm border border-ink bg-surface px-3 py-2">
              {profile.summary || "The agent will summarize once there is something to summarize."}
            </p>
            <p className="mt-2 text-xs">
              {profile.evidence_count} evidence item(s) · wallet{" "}
              <span className="font-mono">{user?.wallet_address}</span>
            </p>

            <label htmlFor="headline" className="block mt-6 text-xs uppercase tracking-wide mb-1">
              Headline
            </label>
            <input
              id="headline"
              value={headline}
              onChange={(e) => setHeadline(e.target.value)}
              className="w-full"
              maxLength={500}
            />
          </>
        ) : (
          <p className="mt-3 text-sm">Loading</p>
        )}
        {error && <p className="mt-3 text-sm text-rust">{error}</p>}
        {notice && <p className="mt-3 text-sm">{notice}</p>}
      </section>

      <section className="lg:col-span-6 lg:border-l border-ink lg:pl-8">
        <h2 className="font-display text-2xl">Privacy, field by field</h2>
        <p className="mt-2 text-sm">
          Uncheck anything and it disappears from your public profile for everyone, including
          recruiters. Nothing is hidden from you here.
        </p>
        <ul className="mt-4 border border-ink divide-y divide-ink">
          {TOGGLES.map((t) => (
            <li key={t.key} className="px-4 py-2 flex items-center justify-between">
              <span className="text-sm">{t.label}</span>
              <label className="flex items-center gap-2 text-xs">
                <span>{toggles[t.key] ? "public" : "private"}</span>
                <input
                  type="checkbox"
                  checked={Boolean(toggles[t.key])}
                  onChange={(e) => setToggles({ ...toggles, [t.key]: e.target.checked })}
                />
              </label>
            </li>
          ))}
        </ul>
        <button onClick={save} disabled={busy} className="mt-4 bg-rust text-paper px-5 py-2 text-sm disabled:opacity-50">
          Save profile
        </button>
        {user && (
          <p className="mt-4 text-xs">
            Public page:{" "}
            <Link to={`/profiles/${user.id}`} className="underline underline-offset-4">
              /profiles/{user.id}
            </Link>
          </p>
        )}
      </section>
    </div>
  );
}
