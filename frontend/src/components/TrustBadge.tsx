import type { TrustState } from "../lib/types";

/**
 * Every credential shows exactly one status. The text label is always present;
 * color is used only for status and border style keeps the states distinct
 * without it: solid double border for Verified, dashed for Unverified, double
 * rule + strike for Revoked, rust for Tampered, dotted for Not found.
 */
const STYLE: Record<TrustState, string> = {
  Verified: "border-[2.5px] border-double border-ink text-emerald-800 font-semibold",
  Unverified: "border border-dashed border-ink text-amber-700",
  Revoked: "border-[3px] border-double border-ink text-red-800 line-through",
  Tampered: "border border-solid border-rust text-rust font-semibold",
  "Not found": "border border-dotted border-ink",
};

const LABEL: Record<TrustState, string> = {
  Verified: "Verified",
  Unverified: "Unverified",
  Revoked: "Revoked",
  Tampered: "Tampered",
  "Not found": "Not found",
};

export default function TrustBadge({ state, className = "" }: { state: TrustState; className?: string }) {
  return (
    <span className={`inline-block bg-paper border px-2 py-0.5 text-xs ${STYLE[state] ?? STYLE["Not found"]} ${className}`}>
      {LABEL[state] ?? state}
    </span>
  );
}
