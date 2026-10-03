import type { TrustState } from "../lib/types";

/**
 * Every credential shows exactly one status. States differ by border style
 * and label (never color alone): solid double border for verified, dashed
 * for AI-extracted, double rule for revoked, rust solid for tampered,
 * dotted for unknown.
 */
const STYLE: Record<TrustState, string> = {
  "Issuer-verified": "border-[2.5px] border-double border-ink font-semibold",
  "AI-extracted (unverified)": "border border-dashed border-ink",
  Revoked: "border-[3px] border-double border-ink line-through",
  Tampered: "border border-solid border-rust text-rust font-semibold",
  Unknown: "border border-dotted border-ink",
};

const LABEL: Record<TrustState, string> = {
  "Issuer-verified": "Issuer-verified",
  "AI-extracted (unverified)": "AI-extracted (unverified)",
  Revoked: "Revoked",
  Tampered: "Tampered",
  Unknown: "Unknown",
};

export default function TrustBadge({ state, className = "" }: { state: TrustState; className?: string }) {
  return (
    <span className={`inline-block border px-2 py-0.5 text-xs ${STYLE[state] ?? STYLE.Unknown} ${className}`}>
      {LABEL[state] ?? state}
    </span>
  );
}
