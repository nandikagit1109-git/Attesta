"""Public verification (feature 1). No login required.

The browser computes SHA-256 with Web Crypto and posts the hash; the backend
looks the hash up on-chain (through its DB index of credential ids) and
reports exactly one of: Verified, Tampered, Revoked, Unknown, plus issuer,
block number, transaction hash and revoke reason for the verify page.
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
    chain.STATUS_UNKNOWN: ("Unknown", "No credential with this id is anchored on-chain"),
    chain.STATUS_VALID: ("Issuer-verified", "On-chain record exists, hash matches, not revoked"),
    chain.STATUS_TAMPERED: ("Tampered", "Presented hash differs from the on-chain record"),
    chain.STATUS_REVOKED: ("Revoked", "The original issuer revoked this credential"),
}


def _verify_hash(db: Session, sha256: str, credential_id: str | None) -> dict:
    sha256 = sha256.lower()

    candidates: list[Credential] = []
    if credential_id:
        by_id = db.query(Credential).filter(Credential.id == credential_id).first()
        if by_id is None:
            raise HTTPException(status_code=404, detail="Credential not found")
        candidates = [by_id]
    else:
        candidates = (
            db.query(Credential).filter(Credential.doc_hash == sha256).all()
        )

    if not candidates:
        db.add(
            AuditLog(
                id=str(uuid.uuid4()),
                actor_id="",
                actor_role="anonymous",
                action="VERIFY",
                object_type="hash",
                object_id=sha256,
                detail={"result": "Unknown"},
            )
        )
        db.commit()
        return {
            "state": TrustState.UNKNOWN.value,
            "reason": "This hash is not anchored on-chain",
            "presented_hash": sha256,
            "onchain_hash": None,
            "candidates": [],
        }

    results = []
    for cred in candidates:
        try:
            status = chain.verify_onchain(cred.chain_credential_id, sha256)
            record = chain.get_onchain_credential(cred.chain_credential_id)
        except chain.ChainError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        state, reason = _STATUS_TO_STATE[status]
        results.append(
            {
                "credential_id": cred.id,
                "state": state,
                "reason": reason,
                "presented_hash": sha256,
                "onchain_hash": record["doc_hash"],
                "hash_match": record["doc_hash"].lower() == f"0x{sha256}",
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
        )

    db.add(
        AuditLog(
            id=str(uuid.uuid4()),
            actor_id="",
            actor_role="anonymous",
            action="VERIFY",
            object_type="hash",
            object_id=sha256,
            detail={"result": results[0]["state"], "candidates": len(results)},
        )
    )
    db.commit()
    # The strongest signal wins for the headline state.
    order = {"Tampered": 0, "Revoked": 1, "Issuer-verified": 2, "Unknown": 3}
    results.sort(key=lambda r: order.get(r["state"], 9))
    headline = dict(results[0])
    headline["candidates"] = results
    return headline


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
