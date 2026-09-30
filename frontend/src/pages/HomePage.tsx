import HealthPanel from "../components/HealthPanel";
import TrustStateBadge from "../components/TrustStateBadge";
import { TRUST_STATES } from "../lib/trustStates";

const threeStates = [
  TRUST_STATES.AI_EXTRACTED,
  TRUST_STATES.ISSUER_VERIFIED,
  TRUST_STATES.REVOKED_OR_TAMPERED,
];

/** Stage 1 placeholder home — shows the trust vocabulary and live backend status. */
export default function HomePage() {
  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <header>
        <p className="text-xs font-semibold uppercase tracking-widest text-indigo-600">
          DecentraHack 2.0 · Stage 1 skeleton
        </p>
        <h1 className="mt-2 text-4xl font-bold tracking-tight text-slate-900">
          TrustPass
        </h1>
        <p className="mt-3 max-w-2xl text-slate-600">
          One skill identity for students: AI agents extract evidence into a skill
          graph, issuers sign credentials on-chain, and recruiters verify hashes and
          revocation without trusting our servers.
        </p>
      </header>

      <section className="mt-10">
        <h2 className="text-lg font-semibold text-slate-900">The three trust states</h2>
        <p className="mt-1 text-sm text-slate-600">
          Every credential surface in this app uses exactly this vocabulary — nothing
          else.
        </p>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          {threeStates.map((s) => (
            <TrustStateBadge key={s} state={s} />
          ))}
        </div>
        <p className="mt-3 text-xs text-slate-500">
          AI analysis is a suggestion, never proof. “Verified” means issuer-signed
          on-chain record AND matching document hash AND not revoked.
        </p>
      </section>

      <section className="mt-8">
        <HealthPanel />
      </section>

      <footer className="mt-12 border-t border-slate-200 pt-6 text-xs text-slate-400">
        MIT licensed · docs: /docs (backend OpenAPI) · trust model: docs/trust-model.md
      </footer>
    </main>
  );
}
