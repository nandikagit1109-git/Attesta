"""Canonical trust states — the single source of truth (backend side).

The frontend mirrors these in `frontend/src/lib/types.ts`.
Never invent a sixth state; never soften "unverified".

- UNVERIFIED: an AI/OCR suggestion extracted from a document.
  It NEVER proves authenticity.
- VERIFIED: issuer-signed on-chain record AND matching document
  hash AND not revoked. All three, together.
- REVOKED: the original issuer revoked the credential (reason + timestamp
  travel with the status).
- TAMPERED: the presented document hash does not match the on-chain record.
- NOT_FOUND: the hash has no on-chain record. Public verify only.

Only the Integrity module (deterministic, no LLM) may emit
VERIFIED, REVOKED or TAMPERED.
"""

from enum import Enum


class TrustState(str, Enum):
    UNVERIFIED = "Unverified"
    VERIFIED = "Verified"
    REVOKED = "Revoked"
    TAMPERED = "Tampered"
    NOT_FOUND = "Not found"


# Serializations of the standard error format: {"error": {"code", "message", "details"}}
class ErrorCode(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    CHAIN_ERROR = "CHAIN_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
