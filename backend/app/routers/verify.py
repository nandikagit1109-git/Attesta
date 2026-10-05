"""Public verification (feature 1). No login required.

The browser computes SHA-256 with Web Crypto and posts the hash. The backend
resolves it through the registry contract's reverse index (document hash ->
credential), falling back to its own DB index only when the node is
unreachable, and reports exactly one of: Verified, Revoked, Not found — plus
Tampered when a specific credential id is supplied and its recorded hash
differs from the presented file. Every response carries issuer, block number,
transaction hash and revoke reason for the verify page.
"""

import hashlib
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import chain
from ..db import get_db
from ..models import AuditLog, Credential
from ..schemas import VerifyHashRequest
from ..services.files import FileRejected, validate_upload
from ..states import TrustState

router = APIRouter(prefix="/api/verify", tags=["verify"])

# Map contract status -> public page state
_STATUS_TO_STATE = {
    chain.STATUS_UNKNOWN: (TrustState.NOT_FOUND.value, "No credential with this id is anchored on-chain"),
    chain.STATUS_VALID: (TrustState.VERIFIED.value, "On-chain record exists, hash matches, not revoked"),
    chain.STATUS_TAMPERED: (TrustState.TAMPERED.value, "Presented hash differs from the on-chain record"),
    chain.STATUS_REVOKED: (TrustState.REVOKED.value, "The original issuer revoked this credential"),
}

_HEADLINE_ORDER = {
    TrustState.TAMPERED.value: 0,
    TrustState.REVOKED.value: 1,
    TrustState.VERIFIED.value: 2,
    TrustState.NOT_FOUND.value: 3,
}


def _audit_verify(db: Session, sha256: str, result_state: str, candidates: int) -> None:
    db.add(
        AuditLog(
            id=str(uuid.uuid4()),
            actor_id="",
            actor_role="anonymous",
            action="VERIFY",
            object_type="hash",
            object_id=sha256,
            detail={"result": result_state, "candidates": candidates},
        )
    )
    db.commit()


def _result_for_credential(cred: Credential, presented: str) -> dict:
    """Verify one credential against a presented hash, on-chain."""
    try:
        status = chain.verify_onchain(cred.chain_credential_id, presented)
        record = chain.get_onchain_credential(cred.chain_credential_id)
    except chain.ChainError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    state, reason = _STATUS_TO_STATE[status]
    return {
        "credential_id": cred.id,
        "state": state,
        "reason": reason,
        "presented_hash": presented,
        "onchain_hash": record["doc_hash"],
        "hash_match": record["doc_hash"].lower() == f"0x{presented}",
        "issuer_address": record["issuer"],
        "recipient_address": record["recipient"],
        "block_number": cred.block_number,
        "tx_hash": cred.tx_hash,
        "issued_at": cred.issued_at.isoformat() if cred.issued_at else None,
        "revoked": record["revoked"],
        "revoked_at": cred.revoked_at.isoformat() if cred.revoked_at else None,
        "revoke_reason": record["revoke_reason"],
        "evidence_title": cred.evidence.title if cred.evidence else "",
    }


def _not_found(db: Session, sha256: str) -> dict:
    _audit_verify(db, sha256, TrustState.NOT_FOUND.value, 0)
    return {
        "state": TrustState.NOT_FOUND.value,
        "reason": "This hash has no record on the registry contract",
        "presented_hash": sha256,
        "onchain_hash": None,
        "candidates": [],
    }


def _verify_hash(db: Session, sha256: str, credential_id: str | None) -> dict:
    sha256 = sha256.lower()

    if credential_id:
        # Specific-credential check: this is the receipt / QR path and the
        # landing page's optional field. A recorded hash that differs from the
        # presented file is Tampered, with the comparison shown.
        by_id = db.query(Credential).filter(Credential.id == credential_id).first()
        if by_id is None:
            raise HTTPException(status_code=404, detail="Credential not found")
        result = _result_for_credential(by_id, sha256)
        _audit_verify(db, sha256, result["state"], 1)
        # Copy into candidates: never let the payload contain itself, or
        # JSON encoding recurses forever.
        return {**result, "candidates": [result]}

    # No-trust path: resolve the bare hash on-chain through the reverse
    # index. The database is only a fallback for a chain outage.
    onchain = None
    try:
        onchain = chain.lookup_by_hash(sha256)
    except chain.ChainError:
        onchain = None  # fall through to the DB index

    if onchain is not None:
        cred = (
            db.query(Credential)
            .filter(Credential.chain_credential_id == onchain["credential_id"])
            .first()
        )
        if cred is None:
            cred = db.query(Credential).filter(Credential.doc_hash == sha256).first()
            # The chain knows the hash but this server has no mirror row
            # (another issuer wrote it). Answer from the chain record alone.
            state = TrustState.REVOKED.value if onchain["revoked"] else TrustState.VERIFIED.value
            result = {
                "credential_id": None,
                "state": state,
                "reason": _STATUS_TO_STATE[
                    chain.STATUS_REVOKED if onchain["revoked"] else chain.STATUS_VALID
                ][1],
                "presented_hash": sha256,
                "onchain_hash": onchain["doc_hash"],
                "hash_match": True,
                "issuer_address": onchain["issuer"],
                "recipient_address": onchain["recipient"],
                "block_number": None,
                "tx_hash": None,
                "issued_at": None,
                "revoked": onchain["revoked"],
                "revoked_at": None,
                "revoke_reason": onchain["revoke_reason"],
                "evidence_title": "",
            }
            _audit_verify(db, sha256, state, 1)
            return {**result, "candidates": [result]}
        result = _result_for_credential(cred, sha256)
        _audit_verify(db, sha256, result["state"], 1)
        return {**result, "candidates": [result]}

    # Fallbacks: chain unreachable (use the DB mirror) or hash unknown
    # on-chain (an un-anchored or tampered file: nothing proves it).
    if chain.is_reachable():
        return _not_found(db, sha256)

    candidates = db.query(Credential).filter(Credential.doc_hash == sha256).all()
    if not candidates:
        return _not_found(db, sha256)

    results = [_result_for_credential(cred, sha256) for cred in candidates]
    results.sort(key=lambda r: _HEADLINE_ORDER.get(r["state"], 9))
    # Copy into candidates: never let the payload contain itself, or
    # JSON encoding recurses forever.
    return {**results[0], "candidates": results}


@router.post("/hash")
def verify_hash(payload: VerifyHashRequest, db: Session = Depends(get_db)):
    return _verify_hash(db, payload.sha256, payload.credential_id)


@router.post("/file")
def verify_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Convenience path for clients that cannot use Web Crypto (and for the
    API tests). The file is validated, hashed and discarded; nothing is
    stored, because the browser path already computes the hash client-side."""
    validate_upload(file)

    digest = hashlib.sha256()
    size = 0
    while True:
        chunk = file.file.read(1024 * 1024)
        if not chunk:
            break
        size += len(chunk)
        if size > 10 * 1024 * 1024:
            raise FileRejected("File exceeds the 10 MB limit")
        digest.update(chunk)
    if size == 0:
        raise FileRejected("Empty file")
    return _verify_hash(db, digest.hexdigest(), None)
