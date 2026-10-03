"""Integrity Agent. Deterministic code, no LLM, the ONLY component allowed
to emit Issuer-verified / Revoked / Tampered.

It hashes the presented document, compares with the on-chain record and
checks revocation. On a chain outage it reports an error flag and leaves the
trust state untouched (the caller keeps the previous state).
"""

from .. import chain
from ..states import TrustState
from .base import AgentContext, AgentResult, BaseAgent


class IntegrityAgent(BaseAgent):
    name = "integrity"

    def run(self, ctx: AgentContext) -> AgentResult:
        evidence = ctx.evidence
        presented: str = ctx.params.get("presented_sha256", "") or (evidence.sha256 if evidence else "")
        credential = ctx.params.get("credential")
        input_summary = (
            f"hash check: presented {presented[:12]}... vs on-chain record "
            f"{(credential.chain_credential_id[:14] + '...') if credential else 'none'}"
        )

        if credential is None:
            return AgentResult(
                input_summary=input_summary,
                output={"trust_state": TrustState.UNKNOWN.value, "reason": "no on-chain credential for this document"},
                confidence=1.0,
                flags=["no-credential"],
                used_fallback=False,
            )

        try:
            status = chain.verify_onchain(credential.chain_credential_id, _to_bytes32(presented))
            record = chain.get_onchain_credential(credential.chain_credential_id)
        except chain.ChainError as exc:
            return AgentResult(
                input_summary=input_summary,
                output={"error": f"chain unavailable: {exc}"},
                confidence=0.0,
                flags=["chain-unavailable"],
                used_fallback=False,
            )

        presented_norm = _to_bytes32(presented).lower()
        base = {
            "credential_id": credential.id,
            "chain_credential_id": credential.chain_credential_id,
            "presented_hash": presented.lower(),
            "onchain_hash": record["doc_hash"],
            "hash_match": record["doc_hash"].lower() == presented_norm,
            "issuer_address": record["issuer"],
            "recipient_address": record["recipient"],
            "block_number": credential.block_number,
            "tx_hash": credential.tx_hash,
            "revoked": record["revoked"],
            "revoked_at": record["revoked_at"],
            "revoke_reason": record["revoke_reason"],
        }

        if status == chain.STATUS_REVOKED:
            state, reason = TrustState.REVOKED, f"Revoked by the issuer: {record['revoke_reason'] or 'no reason given'}"
        elif status == chain.STATUS_TAMPERED:
            state, reason = TrustState.TAMPERED, "Document hash does not match the on-chain record"
        elif status == chain.STATUS_VALID:
            state, reason = TrustState.ISSUER_VERIFIED, "On-chain record exists, hash matches, not revoked"
        else:
            # The DB has a credential the chain no longer knows (for example
            # after a chain reset). "Issuer-verified" requires an on-chain
            # record, so the honest state is Unknown here.
            state, reason = TrustState.UNKNOWN, "Credential not found on-chain"
            base["flags"] = ["chain-record-missing"]
            return AgentResult(
                input_summary=input_summary,
                output={**base, "trust_state": state.value, "reason": reason},
                confidence=1.0,
                flags=["chain-record-missing"],
                used_fallback=False,
            )

        return AgentResult(
            input_summary=input_summary,
            output={**base, "trust_state": state.value, "reason": reason},
            confidence=1.0,
            flags=[],
            used_fallback=False,
        )


def _to_bytes32(hex_hash: str) -> str:
    """Accept a 64-char hex digest and return 0x-prefixed bytes32 form."""
    h = hex_hash.strip().lower()
    if h.startswith("0x"):
        return h
    return "0x" + h
