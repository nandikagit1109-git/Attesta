import { useRef, useState } from "react";
import { sha256File } from "../lib/hash";
import { apiPost } from "../lib/api";
import type { VerifyResult } from "../lib/types";
import VerifyResultPanel from "../components/VerifyResult";

/** Feature 1: public "Verify any file" page, no login required. */
export default function VerifyAnyFile() {
  const [hash, setHash] = useState("");
  const [credentialId, setCredentialId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<VerifyResult | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  async function onFile(file: File | undefined) {
    if (!file) return;
    setResult(null);
    setError("");
    setBusy(true);
    try {
      const sha256 = await sha256File(file);
      setHash(sha256);
      setResult(
        await apiPost<VerifyResult>("/api/verify/hash", {
          sha256,
          credential_id: credentialId.trim() || undefined,
        }),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
      <section className="lg:col-span-4">
        <h1 className="font-display text-3xl font-semibold">Verify any file</h1>
        <p className="mt-3 text-sm leading-relaxed">
          Drop a document. Your browser computes the SHA-256 locally with Web Crypto and the app
          looks the hash up on the registry contract. Nothing is uploaded, no account is needed.
        </p>
        <p className="mt-3 text-sm leading-relaxed">
          The verdict is exactly one of: Verified, Revoked, or Not found — with the issuer
          address, block number and transaction hash. Add a credential ID from a receipt and a
          differing hash is proven Tampered instead.
        </p>
        <div
          className={`mt-6 border border-dashed border-ink p-6 ${dragOver ? "bg-surface" : ""}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            onFile(e.dataTransfer.files?.[0]);
          }}
        >
          <p className="text-sm">Drag a PDF or image here, or</p>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.png,.jpg,.jpeg"
            onChange={(e) => onFile(e.target.files?.[0])}
            className="mt-3 w-full border-0 p-0 text-sm file:mr-3 file:border file:border-ink file:bg-paper file:px-3 file:py-1 file:text-ink file:text-xs"
          />
          <label htmlFor="verify-credential-id" className="block mt-3 text-xs uppercase tracking-wide mb-1">
            Credential ID (optional — enables Tampered)
          </label>
          <input
            id="verify-credential-id"
            type="text"
            value={credentialId}
            onChange={(e) => setCredentialId(e.target.value)}
            placeholder="paste an ID from a receipt"
            className="w-full font-mono text-xs"
          />
        </div>
        {busy && <p className="mt-4 text-sm">Computing SHA-256 and checking the chain. Loading</p>}
        {error && <p className="mt-4 text-sm text-rust">{error}</p>}
        {hash && !busy && (
          <p className="mt-4 font-mono text-[11px] mono-break">SHA-256: {hash}</p>
        )}
      </section>

      <section className="lg:col-span-8">
        {result ? (
          <VerifyResultPanel result={result} directChain />
        ) : (
          <div className="border border-ink bg-surface px-4 py-3 text-sm">
            <p>
              No file checked yet. The result panel will show the verdict, the side-by-side hash
              comparison with the changed hex characters highlighted, and a direct read of the
              issuance transaction from the node.
            </p>
          </div>
        )}
      </section>
    </div>
  );
}
