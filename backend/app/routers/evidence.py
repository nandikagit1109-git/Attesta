"""Evidence endpoints: upload, list, detail, download, tamper demo, verify."""

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..agents.orchestrator import analyze_evidence, verify_evidence
from ..db import get_db
from ..models import AuditLog, Evidence, User
from ..schemas import evidence_public
from ..security import get_current_user, require_roles
from ..services.files import compute_file_sha256, make_tampered_copy, save_upload
from ..states import TrustState

router = APIRouter(prefix="/api/evidence", tags=["evidence"])


def _get_evidence_or_404(db: Session, evidence_id: str) -> Evidence:
    evidence = db.get(Evidence, evidence_id)
    if evidence is None:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return evidence


def _can_view(user: User, evidence: Evidence) -> bool:
    return user.role in ("issuer", "recruiter") or evidence.student_id == user.id


@router.post("")
def upload_evidence(
    title: str = Form(default=""),
    file: UploadFile = File(...),
    user: User = Depends(require_roles("student")),
    db: Session = Depends(get_db),
):
    meta = save_upload(file)

    evidence = Evidence(
        id=str(uuid.uuid4()),
        student_id=user.id,
        title=title.strip()[:300],
        file_name=meta["file_name"],
        stored_path=meta["stored_path"],
        mime_type=meta["mime_type"],
        file_size=meta["file_size"],
        sha256=meta["sha256"],
        extracted={},
        trust_state=TrustState.AI_EXTRACTED.value,
    )
    db.add(evidence)
    db.commit()

    analyze_evidence(db, evidence, user)
    db.refresh(evidence)

    db.add(
        AuditLog(
            id=str(uuid.uuid4()),
            actor_id=user.id,
            actor_role=user.role,
            action="UPLOAD",
            object_type="evidence",
            object_id=evidence.id,
            detail={"file_name": evidence.file_name, "sha256": evidence.sha256},
        )
    )
    db.commit()
    return evidence_public(evidence, include_runs=True, db=db)


@router.get("")
def list_evidence(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Evidence)
    if user.role == "student":
        query = query.filter(Evidence.student_id == user.id)
    rows = query.order_by(Evidence.created_at.desc()).all()
    return [evidence_public(e) for e in rows]


@router.get("/{evidence_id}")
def evidence_detail(
    evidence_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    evidence = _get_evidence_or_404(db, evidence_id)
    if not _can_view(user, evidence):
        raise HTTPException(status_code=403, detail="Not your evidence")
    return evidence_public(evidence, include_runs=True, db=db)


@router.get("/{evidence_id}/file")
def download_evidence(
    evidence_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    evidence = _get_evidence_or_404(db, evidence_id)
    if not _can_view(user, evidence):
        raise HTTPException(status_code=403, detail="Not your evidence")
    return FileResponse(evidence.stored_path, filename=evidence.file_name)


@router.post("/{evidence_id}/tamper")
def tamper_evidence(
    evidence_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Demo feature 5: flip one byte in a stored copy so verification can be
    shown failing with a real hash mismatch."""
    evidence = _get_evidence_or_404(db, evidence_id)
    if evidence.student_id != user.id and user.role != "recruiter":
        raise HTTPException(status_code=403, detail="Only the owner can tamper for the demo")
    if not evidence.tampered_copy_path:
        evidence.tampered_copy_path = make_tampered_copy(evidence.stored_path)
        db.commit()
    return {
        "tampered_sha256": compute_file_sha256(evidence.tampered_copy_path),
        "original_sha256": evidence.sha256,
        "note": "Byte-flipped copy created. Upload it or verify it against the credential to see Tampered.",
    }


@router.get("/{evidence_id}/tamper-file")
def download_tampered(
    evidence_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    evidence = _get_evidence_or_404(db, evidence_id)
    if evidence.student_id != user.id and user.role != "recruiter":
        raise HTTPException(status_code=403, detail="Not your evidence")
    if not evidence.tampered_copy_path:
        evidence.tampered_copy_path = make_tampered_copy(evidence.stored_path)
        db.commit()
    return FileResponse(evidence.tampered_copy_path, filename=f"tampered-{evidence.file_name}")


@router.post("/{evidence_id}/verify")
def verify_evidence_endpoint(
    evidence_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    evidence = _get_evidence_or_404(db, evidence_id)
    if not _can_view(user, evidence):
        raise HTTPException(status_code=403, detail="Not your evidence")
    output = verify_evidence(db, evidence, user)
    db.refresh(evidence)
    return {"verification": output, "evidence": evidence_public(evidence, include_runs=True, db=db)}
