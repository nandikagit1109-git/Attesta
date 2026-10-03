import type { VerifyResult as Result } from "../lib/types";
import TrustBadge from "./TrustBadge";
import HashCompare from "./HashCompare";
import { fmtDate, fmtHash } from "../lib/format";
import { fetchChainInfo, readTxReceipt } from "../lib/onchain";
import type { TxReceiptSummary } from "../lib/onchain";
import { useEffect, useState } from "react";

/**
 * The public verification verdict (features 1 and 7): exactly one headline
 * state, issuer and recipient addresses, block number, transaction hash,
 * revoke reason, and the hash diff. Optionally re-reads the registry
 * contract directly with ethers so the result can be checked without
 * trusting Attesta's servers.
 */
export default function VerifyResult({ result, directChain }: { result: Result; directChain?: boolean }) {
  const [direct, setDirect] = useState<TxReceiptSummary | { error: string } | null>(null);

  useEffect(() => {
    if (!directChain || !result.tx_hash) return;
    let cancelled = false;
    // Re-read the issuance transaction straight from the node by tx hash.
    fetchChainInfo().then(async (info) => {
      if (!info || !info.deployed) return;
      const receipt = await readTxReceipt(result.tx_hash, info);
      if (!cancelled) setDirect(receipt);
    });
    return () => {
      cancelled = true;
    };
  }, [directChain, result.tx_hash]);

  return (
    <div className="border border-ink">
      <div className="border-b border-ink px-4 py-3 flex flex-wrap items-center gap-3">
        <TrustBadge state={result.state} />
        <span className="text-sm">{result.reason}</span>
      </div>

      <dl className="grid grid-cols-1 md:grid-cols-12 divide-y md:divide-y-0 md:divide-x divide-ink">
        <div className="md:col-span-4 px-4 py-3">
          <dt className="text-xs uppercase tracking-wide">Issuer address</dt>
          <dd className="font-mono text-xs mt-1 mono-break">{result.issuer_address || "unknown"}</dd>
          <dt className="text-xs uppercase tracking-wide mt-3">Recipient address</dt>
          <dd className="font-mono text-xs mt-1 mono-break">{result.recipient_address || "unknown"}</dd>
        </div>
        <div className="md:col-span-4 px-4 py-3">
          <dt className="text-xs uppercase tracking-wide">Block number</dt>
          <dd className="font-mono text-xs mt-1">{result.block_number ?? "unknown"}</dd>
          <dt className="text-xs uppercase tracking-wide mt-3">Transaction hash</dt>
          <dd className="font-mono text-xs mt-1 mono-break">{fmtHash(result.tx_hash, 14) || "unknown"}</dd>
        </div>
        <div className="md:col-span-4 px-4 py-3">
          <dt className="text-xs uppercase tracking-wide">Issued</dt>
          <dd className="text-xs mt-1">{fmtDate(result.issued_at) || "unknown"}</dd>
          {result.revoked && (
            <>
              <dt className="text-xs uppercase tracking-wide mt-3">Revoked</dt>
              <dd className="text-xs mt-1">
                {fmtDate(result.revoked_at)}
                {result.revoke_reason ? `: ${result.revoke_reason}` : ""}
              </dd>
            </>
          )}
          <dt className="text-xs uppercase tracking-wide mt-3">Document</dt>
          <dd className="text-xs mt-1">{result.evidence_title || "unknown"}</dd>
        </div>
      </dl>

      <div className="border-t border-ink px-4 py-3">
        <HashCompare presented={result.presented_hash} onchain={result.onchain_hash} />
      </div>

      {result.candidates.length > 1 && (
        <div className="border-t border-ink px-4 py-3 text-sm">
          <p className="mb-2 text-xs uppercase tracking-wide">
            {result.candidates.length} credentials share this hash
          </p>
          <ul className="space-y-1">
            {result.candidates.map((c) => (
              <li key={c.credential_id} className="flex items-center gap-3">
                <TrustBadge state={c.state} />
                <span className="font-mono text-xs">{fmtHash(c.tx_hash, 8)}</span>
                <span className="text-xs">{c.evidence_title}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {directChain && (
        <div className="border-t border-ink px-4 py-3 text-xs">
          {direct && !("error" in direct) ? (
            <p className="font-mono mono-break">
              Direct read from the node: tx {direct.hash.slice(0, 18)}... mined in block
              {" "}
              {direct.blockNumber}, status {direct.status === 1 ? "success" : "failed"},{" "}
              {direct.logCount} event logs. This browser checked the chain itself, without
              Attesta's API.
            </p>
          ) : (
            <p>
              {direct && "error" in direct ? direct.error : "Loading direct chain read."} The verdict
              above comes from the same contract through the API.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
