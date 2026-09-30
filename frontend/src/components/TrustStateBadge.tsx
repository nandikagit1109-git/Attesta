import { TRUST_STATES, TRUST_STATE_STYLES, type TrustState } from "../lib/trustStates";

interface Props {
  state: TrustState;
  size?: "sm" | "md";
}

/** Badge rendering one of the three canonical trust states — nothing else. */
export default function TrustStateBadge({ state, size = "md" }: Props) {
  const style = TRUST_STATE_STYLES[state] ?? TRUST_STATE_STYLES[TRUST_STATES.AI_EXTRACTED];
  const pad = size === "sm" ? "px-2 py-0.5 text-[11px]" : "px-2.5 py-1 text-xs";
  return (
    <span
      title={style.help}
      className={`inline-flex items-center gap-1.5 rounded-full font-semibold ring-1 ${style.badge} ${pad}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} aria-hidden />
      {state}
    </span>
  );
}
