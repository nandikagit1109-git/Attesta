import { useEffect, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { QRCodeCanvas } from "qrcode.react";
import { apiPost } from "../lib/api";
import { sha256File } from "../lib/hash";
import type { VerifyResult } from "../lib/types";
import VerifyResultPanel from "../components/VerifyResult";

/**
 * Feature 3: shareable verification receipt with permalink and QR code.
 * The page verifies the hash baked into the link, and accepts a file drop:
 * the browser hashes it with Web Crypto and checks it against THIS
 * credential, so a tampered copy shows Tampered with the hex diff.
 */
export default function Receipt() {
  const { credentialId } = useParams();
  const [params] = useSearchParams();
  const hash = params.get("hash") ?? "";
  const [result, setResult] = useState<VerifyResult | null>(null);
  const [fileResult, setFileResult] = useState<VerifyResult | null>(null);
  const [fileHash, setFileHash] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const complete = Boolean(credentialId && hash);
  const permalink = `${window.location.origin}/receipt/${credentialId}?hash=${hash}`;

  useEffect(() => {
    if (!complete) return;
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
  }, [credentialId, hash, complete]);

  async function onFile(file: File | undefined) {
    if (!file || !credentialId) return;
    setError("");
    setBusy(true);
    try {
      const sha256 = await sha256File(file);
      setFileHash(sha256);
      setFileResult(await apiPost<VerifyResult>("/api/verify/hash", { sha256, credential_id: credentialId }));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
      <section className="lg:col-span-8">
        <h1 className="font-display text-3xl font-semibold">Verification receipt</h1>
        <p className="mt-2 text-sm">
          Anyone with this link or QR code can re-check the credential on-chain, without an
          account. To test a copy of the document, drop it in the checker below.
        </p>
        <div className="mt-6">
          {busy && <p className="text-sm">Loading</p>}
          {error && <p className="text-sm text-rust">{error}</p>}
          {!complete ? (
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
            <>
              {result && (
                <>
                  <p className="text-xs uppercase tracking-wide mb-2">Linked hash (from the QR / permalink)</p>
                  <VerifyResultPanel result={result} directChain />
                </>
              )}
              {fileResult && (
                <div className="mt-6">
                  <p className="text-xs uppercase tracking-wide mb-2">
                    Dropped file, checked against this credential
                  </p>
                  <VerifyResultPanel result={fileResult} />
                </div>
              )}
            </>
          )}
        </div>
      </section>

      <section className="lg:col-span-4">
        <div className="border border-ink bg-surface p-4">
          <p className="text-xs uppercase tracking-wide mb-3">Scan to verify</p>
          {complete ? (
            <QRCodeCanvas value={permalink} size={180} bgColor="#E4D8C0" fgColor="#2E1F14" />
          ) : (
            <p className="text-sm">QR code appears with a complete link.</p>
          )}
          <p className="mt-3 text-xs uppercase tracking-wide">Permalink</p>
          <p className="mt-1 font-mono text-[11px] mono-break">{complete ? permalink : ""}</p>
          {complete && (
            <button
              className="mt-3 border border-ink px-3 py-1 text-xs"
              onClick={() => navigator.clipboard.writeText(permalink).catch(() => undefined)}
            >
              Copy link
            </button>
          )}
        </div>

        <div className="mt-4 border border-ink p-4">
          <p className="text-xs uppercase tracking-wide mb-2">Check a file against this credential</p>
          <p className="text-xs">
            The file is hashed in your browser and never uploaded. A modified copy will show
            Tampered with the changed hex characters highlighted.
          </p>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.png,.jpg,.jpeg"
            onChange={(e) => onFile(e.target.files?.[0])}
            className="mt-3 w-full border-0 p-0 text-sm file:mr-3 file:border file:border-ink file:bg-paper file:px-3 file:py-1 file:text-ink file:text-xs"
          />
          {fileHash && (
            <p className="mt-2 font-mono text-[11px] mono-break">SHA-256: {fileHash}</p>
          )}
        </div>
      </section>
    </div>
  );
}
