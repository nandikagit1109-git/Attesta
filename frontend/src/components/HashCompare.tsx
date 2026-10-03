import { hashDiffMask } from "../lib/hash";

/**
 * Side-by-side hash comparison (feature 1). Differing hex characters get a
 * rust background so a tampered file is visible at a glance.
 */
export default function HashCompare({
  presented,
  onchain,
}: {
  presented: string;
  onchain: string | null;
}) {
  if (!onchain) {
    return (
      <p className="text-sm">
        No on-chain hash to compare against; this hash is not anchored.
      </p>
    );
  }
  const mask = hashDiffMask(presented.replace(/^0x/, "").toLowerCase(), onchain.replace(/^0x/, "").toLowerCase());
  const diffCount = mask.filter(Boolean).length;

  const renderHash = (hash: string, compare: boolean) => {
    const clean = hash.replace(/^0x/, "").toLowerCase();
    return (
      <span className="font-mono text-xs leading-5 mono-break">
        {compare &&
          clean.split("").map((ch, i) => (
            <span key={i} className={mask[i] ? "bg-rust text-paper" : ""}>
              {ch}
            </span>
          ))}
        {!compare && clean}
      </span>
    );
  };

  return (
    <div className="border border-ink">
      <div className="border-b border-ink px-3 py-2">
        <p className="text-xs uppercase tracking-wide mb-1">Presented file (SHA-256, computed in your browser)</p>
        {renderHash(presented, true)}
      </div>
      <div className="px-3 py-2 bg-surface">
        <p className="text-xs uppercase tracking-wide mb-1">On-chain record (SHA-256, as issued)</p>
        {renderHash(onchain, true)}
      </div>
      <div className="border-t border-ink px-3 py-2 text-xs">
        {diffCount === 0
          ? "Every hex character matches."
          : `${diffCount} of 64 hex characters differ. The file was modified after issuance.`}
      </div>
    </div>
  );
}
