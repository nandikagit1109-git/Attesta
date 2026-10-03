import { Link } from "react-router-dom";
import { useRef, useState } from "react";
import { sha256File } from "../lib/hash";
import { apiPost } from "../lib/api";
import type { VerifyResult } from "../lib/types";
import VerifyResultPanel from "../components/VerifyResult";
import { useAuth } from "../lib/auth";

export default function Landing() {
  const { user } = useAuth();
  const [hash, setHash] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<VerifyResult | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  async function onFile(file: File | undefined) {
    if (!file) return;
    setResult(null);
    setError("");
    setBusy(true);
    try {
      const sha256 = await sha256File(file);
      setHash(sha256);
      setResult(await apiPost<VerifyResult>("/api/verify/hash", { sha256 }));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
      <section className="lg:col-span-7 border-b lg:border-b-0 lg:border-r border-ink lg:pr-8">
        <h1 className="font-display text-5xl leading-[1.05] font-semibold">
          Verified student credentials, proven on-chain.
        </h1>
        <p className="mt-6 text-lg leading-relaxed">
          AI agents read a student's certificates and flag what is missing. An issuer at the
          college confirms the facts. The SHA-256 hash of the document is written to a public
          blockchain, and anyone can check a file later without ever trusting Attesta's servers.
        </p>
        <div className="mt-8 border-t border-ink">
          <div className="grid grid-cols-1 sm:grid-cols-2 divide-y sm:divide-y-0 sm:divide-x divide-ink">
            <div className="py-4 sm:pr-6">
              <p className="font-display text-lg">1. AI-extracted (unverified)</p>
              <p className="text-sm mt-1">
                A suggestion from the agents. Never proof. Clearly labeled everywhere.
              </p>
            </div>
            <div className="py-4 sm:pl-6">
              <p className="font-display text-lg">2. Issuer-verified</p>
              <p className="text-sm mt-1">
                On-chain record exists, the file hash matches and the credential is not revoked.
              </p>
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 divide-y sm:divide-y-0 sm:divide-x divide-ink border-t border-ink">
            <div className="py-4 sm:pr-6">
              <p className="font-display text-lg">3. Revoked / Tampered</p>
              <p className="text-sm mt-1">
                Shown with the reason and timestamp. Revocation is public on the verify page.
              </p>
            </div>
            <div className="py-4 sm:pl-6">
              <p className="font-display text-lg">4. Why a blockchain</p>
              <p className="text-sm mt-1">
                Several independent issuers write records; no tokens, no speculation, just hashes.
              </p>
            </div>
          </div>
        </div>
        <div className="mt-8 flex flex-wrap gap-4 items-center">
          {user ? (
            <Link
              to={user.role === "student" ? "/dashboard" : user.role === "issuer" ? "/issuer" : "/recruiter"}
              className="bg-rust text-paper px-5 py-3 text-sm font-medium"
            >
              Open your desk
            </Link>
          ) : (
            <Link to="/login" className="bg-rust text-paper px-5 py-3 text-sm font-medium">
              Enter the demo
            </Link>
          )}
          <Link to="/verify" className="border border-ink px-5 py-3 text-sm">
            Verify any file
          </Link>
        </div>
      </section>

      <section className="lg:col-span-5">
        <div className="border border-ink bg-surface">
          <div className="border-b border-ink px-4 py-3">
            <h2 className="font-display text-xl">Verify a certificate right now</h2>
            <p className="text-sm mt-1">
              Choose a file. The browser computes its SHA-256 with Web Crypto and looks it up
              on-chain. The file itself is never uploaded.
            </p>
          </div>
          <div className="px-4 py-4">
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.png,.jpg,.jpeg"
              onChange={(e) => onFile(e.target.files?.[0])}
              className="w-full border-0 p-0 text-sm file:mr-3 file:border file:border-ink file:bg-paper file:px-3 file:py-1 file:text-ink file:text-xs"
            />
            {busy && <p className="mt-3 text-sm">Computing SHA-256 and checking the chain. Loading</p>}
            {error && <p className="mt-3 text-sm text-rust">{error}</p>}
            {hash && !busy && (
              <p className="mt-3 font-mono text-[11px] mono-break">
                SHA-256: {hash}
              </p>
            )}
          </div>
          {result && (
            <div className="border-t border-ink px-4 py-4">
              <VerifyResultPanel result={result} />
            </div>
          )}
        </div>
        <p className="mt-3 text-xs">
          Try it: upload any PDF here, then modify one byte of a copy and verify that copy to see
          the Tampered state.
        </p>
      </section>
    </div>
  );
}
