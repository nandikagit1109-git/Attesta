"""Credentials endpoints: issuer approval queue, on-chain issue, revoke,
listing, and CSV bulk issuance (feature 8)."""

import csv
import io
import os
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import chain
from ..agents.orchestrator import analyze_evidence, verify_evidence
from ..db import get_db
from ..models import AuditLog, Credential, Evidence, User
from ..schemas import (
    DEFAULT_PUBLIC_FIELDS,
    IssueRequest,
    RevokeRequest,
    credential_public,
    evidence_public,
)
from ..security import get_current_user, hash_password, require_roles
from ..states import TrustState

router = APIRouter(prefix="/api/credentials", tags=["credentials"])


def _require_wallet(user: User) -> str:
    if not user.wallet_address:
        raise HTTPException(
            status_code=409, detail="Student wallet not generated yet; re-register or contact support"
        )
    return user.wallet_address


@router.get("/queue")
def issuer_queue(user: User = Depends(require_roles("issuer")), db: Session = Depends(get_db)):
    """Evidence awaiting issuer approval, plus already-issued records."""
    pending = (
        db.query(Evidence)
        .filter(Evidence.credential == None)  # noqa: E711  (SQLAlchemy is-null)
        .order_by(Evidence.created_at.desc())
        .all()
    )
    issued = (
        db.query(Credential)
        .filter(Credential.issuer_id == user.id)
        .order_by(Credential.issued_at.desc())
        .all()
    )
    return {
        "pending": [evidence_public(e) for e in pending],
        "issued": [credential_public(c) for c in issued],
    }


@router.post("/issue")
def issue_credential(
    payload: IssueRequest,
    user: User = Depends(require_roles("issuer")),
    db: Session = Depends(get_db),
):
    """Approve an evidence: anchor its SHA-256 on-chain, then verify it."""
    evidence = db.get(Evidence, payload.evidence_id)
    if evidence is None:
        raise HTTPException(status_code=404, detail="Evidence not found")
    if evidence.credential is not None:
        raise HTTPException(status_code=409, detail="This evidence already has a credential")

    student = evidence.student
    recipient = _require_wallet(student)

    try:
        result = chain.issue_onchain(evidence.sha256, recipient)
    except chain.ChainError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    credential = Credential(
        id=str(uuid.uuid4()),
        chain_credential_id=result["chain_credential_id"],
        evidence_id=evidence.id,
        issuer_id=user.id,
        recipient_address=recipient,
        doc_hash=evidence.sha256,
        tx_hash=result["tx_hash"],
        block_number=result["block_number"],
    )
    db.add(credential)
    db.commit()
    db.refresh(credential)

    # Immediately run the Integrity Agent so the status is earned, not assumed.
    verify_evidence(db, evidence, user)
    db.refresh(evidence)

    db.add(
        AuditLog(
            id=str(uuid.uuid4()),
            actor_id=user.id,
            actor_role=user.role,
            action="ISSUE",
            object_type="credential",
            object_id=credential.id,
            detail={
                "evidence_id": evidence.id,
                "tx_hash": credential.tx_hash,
                "block_number": credential.block_number,
            },
        )
    )
    db.commit()
    return {
        "credential": credential_public(credential),
        "evidence": evidence_public(evidence, include_runs=True, db=db),
    }


@router.post("/{credential_id}/revoke")
def revoke_credential(
    credential_id: str,
    payload: RevokeRequest,
    user: User = Depends(require_roles("issuer")),
    db: Session = Depends(get_db),
):
    """Only the original issuer can revoke (enforced on-chain and here)."""
    reason = payload.reason.strip()

    credential = db.get(Credential, credential_id)
    if credential is None:
        raise HTTPException(status_code=404, detail="Credential not found")
    if credential.issuer_id != user.id:
        raise HTTPException(status_code=403, detail="Only the original issuer can revoke")
    if credential.revoked:
        raise HTTPException(status_code=409, detail="Credential already revoked")

    try:
        chain.revoke_onchain(credential.chain_credential_id, reason)
    except chain.ChainError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    credential.revoked = True
    credential.revoked_at = datetime.now(UTC)
    credential.revoke_reason = reason[:300]
    evidence = credential.evidence
    if evidence:
        evidence.trust_state = TrustState.REVOKED.value

    db.add(
        AuditLog(
            id=str(uuid.uuid4()),
            actor_id=user.id,
            actor_role=user.role,
            action="REVOKE",
            object_type="credential",
            object_id=credential.id,
            detail={"reason": credential.revoke_reason},
        )
    )
    db.commit()
    return credential_public(credential)


@router.get("")
def list_credentials(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Issuers see what they issued; students see what they hold; recruiters
    see the public registry view."""
    query = db.query(Credential)
    if user.role == "issuer":
        query = query.filter(Credential.issuer_id == user.id)
    elif user.role == "student":
        query = query.join(Evidence, Credential.evidence_id == Evidence.id).filter(
            Evidence.student_id == user.id
        )
    rows = query.order_by(Credential.issued_at.desc()).all()
    return [credential_public(c) for c in rows]


@router.post("/bulk")
def bulk_issue_csv(
    file: UploadFile,
    user: User = Depends(require_roles("issuer")),
    db: Session = Depends(get_db),
):
    """CSV bulk issuance. Columns: student_email, title, file_name.
    Each row becomes a real PDF (labeled Sample data), an evidence for the
    student, and an on-chain credential issued by the demo issuer."""
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=422, detail="Upload a .csv file with columns student_email,title,file_name")
    try:
        text = file.file.read().decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="CSV must be UTF-8 encoded") from exc
    if len(text) > 2_000_000:
        raise HTTPException(status_code=422, detail="CSV too large (2 MB limit)")

    reader = csv.DictReader(io.StringIO(text))
    required_cols = {"student_email", "title", "file_name"}
    if not reader.fieldnames or not required_cols.issubset({c.strip().lower() for c in reader.fieldnames}):
        raise HTTPException(
            status_code=422,
            detail="CSV must have the columns: student_email,title,file_name",
        )

    results = []
    for row in reader:
        email = (row.get("student_email") or "").strip().lower()
        title = (row.get("title") or "").strip()
        file_name = (row.get("file_name") or "").strip() or "certificate.pdf"
        if not email or not title:
            results.append({"student_email": email, "status": "error", "error": "missing email or title"})
            continue
        try:
            cred, ev = _issue_for_row(db, user, email, title, file_name)
            results.append(
                {
                    "student_email": email,
                    "status": "issued",
                    "evidence_id": ev.id,
                    "credential_id": cred.id,
                    "tx_hash": cred.tx_hash,
                }
            )
        except Exception as exc:
            results.append({"student_email": email, "status": "error", "error": str(exc)[:200]})

    db.add(
        AuditLog(
            id=str(uuid.uuid4()),
            actor_id=user.id,
            actor_role=user.role,
            action="BULK_ISSUE",
            object_type="credential",
            object_id="",
            detail={"rows": len(results), "ok": sum(1 for r in results if r["status"] == "issued")},
        )
    )
    db.commit()
    return {"results": results}


def _issue_for_row(db: Session, issuer: User, email: str, title: str, file_name: str):
    """Create (or reuse) the student, a sample PDF, the evidence row and the
    on-chain credential for one CSV row."""
    from ..services.sample_docs import write_sample_certificate_pdf

    student = db.query(User).filter(User.email == email).first()
    if student is None:
        from ..security import generate_wallet

        address, key = generate_wallet()
        student = User(
            id=str(uuid.uuid4()),
            email=email,
            password_hash=hash_password(uuid.uuid4().hex),  # account claim flow out of demo scope
            full_name=email.split("@")[0].replace(".", " ").title(),
            role="student",
            public_fields=dict(DEFAULT_PUBLIC_FIELDS),
            wallet_address=address,
            wallet_private_key=key,
        )
        db.add(student)
        db.commit()

    pdf_path, sha256 = write_sample_certificate_pdf(student, title, issuer.org_name or issuer.full_name)
    evidence = Evidence(
        id=str(uuid.uuid4()),
        student_id=student.id,
        title=title,
        file_name=file_name,
        stored_path=pdf_path,
        mime_type="application/pdf",
        file_size=os.path.getsize(pdf_path),
        sha256=sha256,
        extracted={},
        trust_state=TrustState.AI_EXTRACTED.value,
    )
    db.add(evidence)
    db.commit()
    analyze_evidence(db, evidence, issuer)

    recipient = student.wallet_address or _require_wallet(student)
    result = chain.issue_onchain(evidence.sha256, recipient)
    credential = Credential(
        id=str(uuid.uuid4()),
        chain_credential_id=result["chain_credential_id"],
        evidence_id=evidence.id,
        issuer_id=issuer.id,
        recipient_address=recipient,
        doc_hash=evidence.sha256,
        tx_hash=result["tx_hash"],
        block_number=result["block_number"],
    )
    db.add(credential)
    db.commit()
    verify_evidence(db, evidence, issuer)
    return credential, evidence
