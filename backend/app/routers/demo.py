"""Demo/Admin utilities: reset the sample dataset and the one-click tamper.

Both belong to the Demo/Admin role (the third demo login button). Both are
deliberately destructive, so in production they refuse to run: a hosted
deployment can never have its data wiped or its files mutated by a stray
click. Run the demo locally with ./make demo-check or the dev server.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models import AuditLog, Credential
from ..security import require_roles
from ..services.demo_seed import reset_demo_data
from ..services.files import compute_file_sha256, make_tampered_copy
from ..states import TrustState

router = APIRouter(prefix="/api/demo", tags=["demo"], dependencies=[Depends(require_roles("admin"))])


def _dev_only() -> None:
    if get_settings().environment == "production":
        raise HTTPException(status_code=403, detail="Demo controls are disabled in production")


@router.post("/reset")
def reset(db: Session = Depends(get_db)):
    _dev_only()
    return reset_demo_data(db)


@router.post("/tamper/{credential_id}")
def tamper(credential_id: str, db: Session = Depends(get_db)):
    """One-click tamper for the demo: flip one byte in a stored copy of the
    credential's document, mark the credential page HASH MISMATCH immediately
    and write an off-chain tamper-detection entry. The on-chain record stays
    untouched — the registry cannot be edited, which is exactly the point."""
    _dev_only()

    credential = db.get(Credential, credential_id)
    if credential is None:
        raise HTTPException(status_code=404, detail="Credential not found")
    evidence = credential.evidence
    if evidence is None:
        raise HTTPException(status_code=404, detail="Evidence not found for this credential")

    tampered_path = evidence.tampered_copy_path
    if not tampered_path:
        tampered_path = make_tampered_copy(evidence.stored_path)
        evidence.tampered_copy_path = tampered_path

    tampered_sha256 = compute_file_sha256(tampered_path)

    # The credential page shows the mismatch right away, without waiting for
    # anyone to run a verification. The on-chain record is never touched.
    evidence.trust_state = TrustState.TAMPERED.value
    db.add(
        AuditLog(
            id=str(uuid.uuid4()),
            actor_id="",
            actor_role="demo-admin",
            action="TAMPER",
            object_type="credential",
            object_id=credential.id,
            detail={
                "source": "off-chain",
                "original_sha256": evidence.sha256,
                "tampered_sha256": tampered_sha256,
            },
        )
    )
    db.commit()
    db.refresh(evidence)

    return {
        "credential_id": credential.id,
        "evidence_id": evidence.id,
        "original_sha256": evidence.sha256,
        "tampered_sha256": tampered_sha256,
        "note": (
            "Byte-flipped copy created and the credential page now shows HASH MISMATCH. "
            "The on-chain record is untouched. Verify the tampered copy against this "
            "credential to see Tampered with the differing hex characters highlighted."
        ),
    }
