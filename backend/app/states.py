"""Canonical trust states — the single source of truth (backend side).

The frontend mirrors these in `frontend/src/lib/trustStates.ts`.
Never invent a fourth state; never soften "unverified".

- AI_EXTRACTED: an AI/OCR suggestion extracted from a document.
  It NEVER proves authenticity.
- ISSUER_VERIFIED: issuer-signed on-chain record AND matching document
  hash AND not revoked. All three, together.
- REVOKED_OR_TAMPERED: revoked on-chain, or hash mismatch.

Only the Integrity Agent (deterministic, no LLM) may emit
ISSUER_VERIFIED or REVOKED_OR_TAMPERED.
"""

from enum import Enum


class TrustState(str, Enum):
    AI_EXTRACTED = "AI-extracted (unverified)"
    ISSUER_VERIFIED = "Issuer-verified"
    REVOKED_OR_TAMPERED = "Revoked or tampered"


# Serializations of the standard error format: {"error": {"code", "message", "details"}}
class ErrorCode(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    CHAIN_ERROR = "CHAIN_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
