"""Canonical trust states — the single source of truth (backend side).

The frontend mirrors these in `frontend/src/lib/trustStates.ts`.
Never invent a fifth state; never soften "unverified".

- AI_EXTRACTED: an AI/OCR suggestion extracted from a document.
  It NEVER proves authenticity.
- ISSUER_VERIFIED: issuer-signed on-chain record AND matching document
  hash AND not revoked. All three, together.
- REVOKED: the original issuer revoked the credential (reason + timestamp
  travel with the status).
- TAMPERED: the presented document hash does not match the on-chain record.
- UNKNOWN: the hash or credential id is not on-chain. Public verify only.

Only the Integrity Agent (deterministic, no LLM) may emit
ISSUER_VERIFIED, REVOKED or TAMPERED.
"""

from enum import Enum


class TrustState(str, Enum):
    AI_EXTRACTED = "AI-extracted (unverified)"
    ISSUER_VERIFIED = "Issuer-verified"
    REVOKED = "Revoked"
    TAMPERED = "Tampered"
    UNKNOWN = "Unknown"


# Serializations of the standard error format: {"error": {"code", "message", "details"}}
class ErrorCode(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    CHAIN_ERROR = "CHAIN_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
