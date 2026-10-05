"""Canonical demo dataset, shared by scripts/seed_demo.py and the
/api/demo/reset endpoint (the Admin "Reset demo data" button).

Contents per the revised spec: 1 student (with a guest share token), 1
college issuer, 1 demo admin; 3 certificate PDFs (Python, SQL, Excel)
generated as real files; 2 issued on-chain credentials (the SQL one then
revoked with a reason); 1 pre-staged tampered copy of the Python
certificate; 2 student projects. Everything is labeled Sample data.
"""

import os
import secrets
import uuid

from sqlalchemy.orm import Session

from .. import chain
from ..agents.orchestrator import analyze_evidence, verify_evidence
from ..models import AgentRun, AuditLog, Credential, Evidence, Project, User
from ..security import generate_wallet, hash_password
from ..services.files import make_tampered_copy
from ..services.sample_docs import write_sample_certificate_pdf
from ..states import TrustState
from .files import compute_file_sha256


def _demo_spec() -> dict[str, dict[str, str]]:
    """Same demo identities as the login screen (imported to avoid drift)."""
    from ..routers.auth import DEMO_PASSWORD, DEMO_USERS

    return {role: {**spec, "password": DEMO_PASSWORD} for role, spec in DEMO_USERS.items()}


def _clear(db: Session) -> None:
    for model in (AgentRun, AuditLog, Credential, Evidence, Project, User):
        db.query(model).delete()
    db.commit()


def _make_user(db: Session, role: str, spec: dict[str, str]) -> User:
    wallet_address, wallet_key = ("", "")
    if role == "student":
        wallet_address, wallet_key = generate_wallet()
    user = User(
        id=str(uuid.uuid4()),
        email=spec["email"],
        password_hash=hash_password(spec["password"]),
        full_name=spec["full_name"],
        role=role,
        org_name=spec.get("org_name", ""),
        headline=spec.get("headline", ""),
        public_fields={
            "full_name": True,
            "headline": True,
            "skills": True,
            "projects": True,
            "credentials": True,
            "email": False,
        },
        wallet_address=wallet_address,
        wallet_private_key=wallet_key,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _certificate(db: Session, student: User, actor: User, title: str) -> Evidence:
    path, sha256 = write_sample_certificate_pdf(student, title, "Springfield College")
    evidence = Evidence(
        id=str(uuid.uuid4()),
        student_id=student.id,
        title=title,
        file_name=f"{title.lower().replace(' ', '-')}-certificate.pdf",
        stored_path=path,
        mime_type="application/pdf",
        file_size=os.path.getsize(path),
        sha256=sha256,
        extracted={},
        trust_state=TrustState.UNVERIFIED.value,
    )
    db.add(evidence)
    db.commit()
    analyze_evidence(db, evidence, actor)
    db.refresh(evidence)
    return evidence


def _issue(db: Session, evidence: Evidence, issuer: User) -> Credential:
    student = evidence.student
    result = chain.issue_onchain(evidence.sha256, student.wallet_address)
    credential = Credential(
        id=str(uuid.uuid4()),
        chain_credential_id=result["chain_credential_id"],
        evidence_id=evidence.id,
        issuer_id=issuer.id,
        recipient_address=student.wallet_address,
        doc_hash=evidence.sha256,
        tx_hash=result["tx_hash"],
        block_number=result["block_number"],
    )
    db.add(credential)
    db.commit()
    db.refresh(credential)
    verify_evidence(db, evidence, issuer)
    db.refresh(evidence)
    return credential


def reset_demo_data(db: Session) -> dict:
    """Wipe and rebuild the demo dataset. Returns a summary the demo check
    prints and the verify steps use."""
    _clear(db)
    spec = _demo_spec()
    student = _make_user(db, "student", spec["student"])
    issuer = _make_user(db, "issuer", spec["issuer"])
    _admin = _make_user(db, "admin", spec["admin"])

    # The student's guest share link: recruiters open /s/<token>, no login.
    student.share_token = secrets.token_urlsafe(24)
    db.commit()

    # 3 certificates: Python (verified), SQL (issued then revoked), Excel (stays unverified).
    py_ev = _certificate(db, student, issuer, "Python Programming")
    sql_ev = _certificate(db, student, issuer, "SQL for Data Analysis")
    excel_ev = _certificate(db, student, issuer, "Excel for Analysts")

    py_cred = _issue(db, py_ev, issuer)
    sql_cred = _issue(db, sql_ev, issuer)

    # Revoke the SQL credential with a visible reason (feature 7).
    revoke_reason = "Sample data: enrollment cancelled by the registrar"
    chain.revoke_onchain(sql_cred.chain_credential_id, revoke_reason)
    sql_cred.revoked = True
    from datetime import UTC, datetime

    sql_cred.revoked_at = datetime.now(UTC)
    sql_cred.revoke_reason = revoke_reason
    sql_ev.trust_state = TrustState.REVOKED.value
    db.commit()

    # Pre-stage the tampered copy of the verified certificate (feature 5).
    tampered_path = make_tampered_copy(py_ev.stored_path)
    py_ev.tampered_copy_path = tampered_path
    tampered_sha256 = compute_file_sha256(tampered_path)
    db.commit()
    # A bare tampered hash proves nothing (it is anchored nowhere), so the
    # summary carries the credential id the verify call must pass to see
    # Tampered (as the receipt permalink and QR code do).

    # 2 projects (feature: student adds a project; graph + career gap use it).
    db.add(
        Project(
            id=str(uuid.uuid4()),
            student_id=student.id,
            title="Retail sales dashboard (Sample data)",
            description="Sample project: a dashboard exploring a public retail dataset.",
            skills=["data-visualization", "sql", "excel"],
        )
    )
    db.add(
        Project(
            id=str(uuid.uuid4()),
            student_id=student.id,
            title="Weather data pipeline (Sample data)",
            description="Sample project: a small ETL job from a public weather API to SQLite.",
            skills=["python", "etl"],
        )
    )

    db.add(
        AuditLog(
            id=str(uuid.uuid4()),
            actor_id=issuer.id,
            actor_role="issuer",
            action="SEED",
            object_type="demo",
            object_id="",
            detail={"certificates": 3, "credentials": 2, "revoked": 1, "tampered": 1},
        )
    )
    db.commit()

    return {
        "student": {"id": student.id, "email": student.email, "wallet": student.wallet_address},
        "issuer": {"id": issuer.id, "email": issuer.email},
        "share_token": student.share_token,
        "verified": {"evidence_id": py_ev.id, "sha256": py_ev.sha256, "credential_id": py_cred.id},
        "revoked": {"evidence_id": sql_ev.id, "sha256": sql_ev.sha256, "credential_id": sql_cred.id},
        "unverified": {"evidence_id": excel_ev.id, "sha256": excel_ev.sha256},
        "tampered": {"sha256": tampered_sha256, "credential_id": py_cred.id},
    }
