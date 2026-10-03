import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { QRCodeCanvas } from "qrcode.react";
import { apiPost } from "../lib/api";
import type { VerifyResult } from "../lib/types";
import VerifyResultPanel from "../components/VerifyResult";

/** Feature 3: shareable verification receipt with permalink and QR code. */
export default function Receipt() {
  const { credentialId } = useParams();
  const [params] = useSearchParams();
  const hash = params.get("hash") ?? "";
  const [result, setResult] = useState<VerifyResult | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const permalink = `${window.location.origin}/receipt/${credentialId}?hash=${hash}`;

  useEffect(() => {
    if (!credentialId || !hash) return;
    let cancelled = false;
    setBusy(true);
    apiPost<VerifyResult>("/api/verify/hash", { sha256: hash, credential_id: credentialId })
      .then((r) => {
        if (!cancelled) setResult(r);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => {
        if (!cancelled) setBusy(false);
      });
    return () => {
      cancelled = true;
    };
  }, [credentialId, hash]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
      <section className="lg:col-span-8">
        <h1 className="font-display text-3xl font-semibold">Verification receipt</h1>
        <p className="mt-2 text-sm">
          Anyone with this link can re-check the credential on-chain. This page loads no personal
          data beyond the credential record itself.
        </p>
        <div className="mt-6">
          {busy && <p className="text-sm">Loading</p>}
          {error && <p className="text-sm text-rust">{error}</p>}
          {!credentialId || !hash ? (
            <div className="border border-ink bg-surface px-4 py-3 text-sm">
              <p>
                This receipt link is incomplete. Share the receipt from an evidence page so the
                permalink carries the document hash.
              </p>
              <p className="mt-2">
                <Link to="/verify" className="underline underline-offset-4">
                  Verify a file manually instead
                </Link>
              </p>
            </div>
          ) : (
            result && <VerifyResultPanel result={result} directChain />
          )}
        </div>
      </section>

      <section className="lg:col-span-4">
        <div className="border border-ink bg-surface p-4">
          <p className="text-xs uppercase tracking-wide mb-3">Scan to verify</p>
          {hash && credentialId ? (
            <QRCodeCanvas value={permalink} size={180} bgColor="#E4D8C0" fgColor="#2E1F14" />
          ) : (
            <p className="text-sm">QR code appears with a complete link.</p>
          )}
          <p className="mt-3 text-xs uppercase tracking-wide">Permalink</p>
          <p className="mt-1 font-mono text-[11px] mono-break">{hash && credentialId ? permalink : ""}</p>
          {hash && credentialId && (
            <button
              className="mt-3 border border-ink px-3 py-1 text-xs"
              onClick={() => navigator.clipboard.writeText(permalink).catch(() => undefined)}
            >
              Copy link
            </button>
          )}
        </div>
      </section>
    </div>
  );
}
