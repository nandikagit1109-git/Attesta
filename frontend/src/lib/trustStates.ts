/**
 * Mirror of backend/app/states.py — the ONLY trust vocabulary allowed in the UI.
 * Never invent a fourth state; never soften "unverified".
 */
export const TRUST_STATES = {
  AI_EXTRACTED: "AI-extracted (unverified)",
  ISSUER_VERIFIED: "Issuer-verified",
  REVOKED_OR_TAMPERED: "Revoked or tampered",
} as const;

export type TrustState = (typeof TRUST_STATES)[keyof typeof TRUST_STATES];

export const TRUST_STATE_LIST: TrustState[] = Object.values(TRUST_STATES);

/** Visual style per state (colors from the trust palette in tailwind.config.js). */
export const TRUST_STATE_STYLES: Record<
  TrustState,
  { badge: string; dot: string; help: string }
> = {
  [TRUST_STATES.AI_EXTRACTED]: {
    badge: "bg-amber-100 text-amber-800 ring-amber-300",
    dot: "bg-amber-500",
    help: "AI suggestion extracted from a document — never proof of authenticity.",
  },
  [TRUST_STATES.ISSUER_VERIFIED]: {
    badge: "bg-emerald-100 text-emerald-800 ring-emerald-300",
    dot: "bg-emerald-500",
    help: "Issuer-signed on-chain record AND document hash matches AND not revoked.",
  },
  [TRUST_STATES.REVOKED_OR_TAMPERED]: {
    badge: "bg-rose-100 text-rose-800 ring-rose-300",
    dot: "bg-rose-500",
    help: "Revoked by the issuer on-chain, or the document hash no longer matches.",
  },
};
