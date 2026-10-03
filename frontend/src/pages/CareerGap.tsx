import { useCallback, useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { apiGet } from "../lib/api";
import type { CareerGap, RolesResponse } from "../lib/types";

/** Career Mentor view: verified skills count above unverified ones. */
export default function CareerGapPage() {
  const [roles, setRoles] = useState<RolesResponse | null>(null);
  const [roleId, setRoleId] = useState("");
  const [gap, setGap] = useState<CareerGap | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    apiGet<RolesResponse>("/api/career/roles")
      .then((r) => {
        setRoles(r);
        setRoleId(r.default ?? r.roles[0]?.id ?? "");
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  const load = useCallback(async (id: string) => {
    setBusy(true);
    setError("");
    try {
      setGap(await apiGet<CareerGap>(`/api/career/gap${id ? `?role=${encodeURIComponent(id)}` : ""}`));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    if (roleId) load(roleId);
  }, [roleId, load]);

  const chartData =
    gap?.missing.slice(0, 8).map((m) => ({ skill: m.skill_id, weight: Math.round(m.weight * 100) })) ?? [];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
      <section className="lg:col-span-4 lg:border-r border-ink lg:pr-8">
        <h1 className="font-display text-3xl font-semibold">Career gap</h1>
        <p className="mt-3 text-sm">
          The Career Mentor compares your verified skills to a target role. Issuer-verified skills
          count in full; unverified ones count at 40 percent and are listed separately.
        </p>
        <label htmlFor="role" className="block mt-6 text-xs uppercase tracking-wide mb-1">
          Target role
        </label>
        <select id="role" value={roleId} onChange={(e) => setRoleId(e.target.value)} className="w-full">
          {roles?.roles.map((r) => (
            <option key={r.id} value={r.id}>
              {r.title}
            </option>
          ))}
        </select>
        <p className="mt-2 text-xs">{roles?.roles.find((r) => r.id === roleId)?.description}</p>
        {busy && <p className="mt-4 text-sm">Loading</p>}
        {error && <p className="mt-4 text-sm text-rust">{error}</p>}
      </section>

      <section className="lg:col-span-8">
        {gap ? (
          <>
            <div className="flex flex-wrap items-baseline gap-6 border border-ink px-4 py-3">
              <div>
                <p className="text-xs uppercase tracking-wide">Match score</p>
                <p className="font-display text-5xl font-semibold">{gap.score}/100</p>
              </div>
              <p className="text-sm max-w-sm">{gap.reasoning}</p>
            </div>

            <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="md:col-span-1">
                <h2 className="text-xs uppercase tracking-wide border-b border-ink pb-1">
                  Verified matches
                </h2>
                <ul className="mt-2 text-sm space-y-1">
                  {gap.matched.length === 0 && <li>None yet. Get a certificate approved.</li>}
                  {gap.matched.map((m) => (
                    <li key={m.skill_id}>
                      <span className="font-mono text-xs">{m.skill_id}</span>
                    </li>
                  ))}
                </ul>
                <h2 className="mt-4 text-xs uppercase tracking-wide border-b border-ink pb-1">
                  Unverified matches (not counted in full)
                </h2>
                <ul className="mt-2 text-sm space-y-1">
                  {gap.unverified.length === 0 && <li>None.</li>}
                  {gap.unverified.map((m) => (
                    <li key={m.skill_id}>
                      <span className="font-mono text-xs">{m.skill_id}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="md:col-span-2">
                <h2 className="text-xs uppercase tracking-wide border-b border-ink pb-1">
                  Missing skills, by priority
                </h2>
                <ul className="mt-2 text-sm space-y-1">
                  {gap.missing.length === 0 && <li>Nothing missing. You cover the whole role.</li>}
                  {gap.missing.map((m) => (
                    <li key={m.skill_id} className="flex items-center justify-between gap-3">
                      <span className="font-mono text-xs">{m.skill_id}</span>
                      <span className="text-xs">{m.priority} priority</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {chartData.length > 0 && (
              <div className="mt-8">
                <h2 className="text-xs uppercase tracking-wide border-b border-ink pb-1">
                  Weight of the top missing skills in the role
                </h2>
                <div className="mt-3 h-56">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
                      <CartesianGrid stroke="#2E1F14" strokeOpacity={0.25} vertical={false} />
                      <XAxis
                        dataKey="skill"
                        tick={{ fill: "#2E1F14", fontSize: 10, fontFamily: "IBM Plex Mono" }}
                        interval={0}
                        angle={-30}
                        textAnchor="end"
                        height={60}
                      />
                      <YAxis tick={{ fill: "#2E1F14", fontSize: 10 }} />
                      <Tooltip
                        contentStyle={{
                          background: "#E4D8C0",
                          border: "1px solid #2E1F14",
                          borderRadius: 0,
                          fontSize: 12,
                        }}
                      />
                      <Bar dataKey="weight" fill="#B4451F" isAnimationActive={false} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            <div className="mt-8">
              <h2 className="text-xs uppercase tracking-wide border-b border-ink pb-1">
                Three project ideas to close the gap
              </h2>
              <ol className="mt-2 text-sm list-decimal list-inside space-y-2">
                {gap.project_ideas.map((idea, i) => (
                  <li key={i}>{idea}</li>
                ))}
              </ol>
            </div>
          </>
        ) : (
          <p className="text-sm">Loading</p>
        )}
      </section>
    </div>
  );
}
