"""Guest recruiter view (feature 4). No login, ever.

A student publishes one long random token; the share link and QR code carry
it. The token is the only key: it grants read access to exactly one
published profile — statuses, skills with confidence, on-chain proof and the
agent trace — and nothing else. There is no directory, no search, no file
download, and tokens cannot be enumerated.
"""



from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..agents.orchestrator import collect_skill_sets, job_match, profile_summary
from ..db import get_db
from ..models import AgentRun, Credential, Evidence, Project, User
from ..schemas import JobMatchRequest, agent_run_public, project_public
from ..states import TrustState

router = APIRouter(prefix="/api/share", tags=["share"])


def _user_by_token(db: Session, token: str) -> User:
    user = db.query(User).filter(User.share_token == token).first()
    if user is None or user.role != "student":
        raise HTTPException(status_code=404, detail="Share link not found")
    return user


def _credential_status(credential: Credential, evidence: Evidence | None) -> str:
    """Status for the share view. Revocation dominates; an off-chain tamper
    detection on the credential page shows next; otherwise the credential is
    Verified (it was anchored with a matching hash and not revoked)."""
    if credential.revoked:
        return TrustState.REVOKED.value
    if evidence is not None and evidence.trust_state == TrustState.TAMPERED.value:
        return TrustState.TAMPERED.value
    return TrustState.VERIFIED.value


@router.get("/{token}")
def shared_profile(token: str, db: Session = Depends(get_db)):
    user = _user_by_token(db, token)

    verified_ids, _unverified = collect_skill_sets(db, user)
    evidences = (
        db.query(Evidence).filter(Evidence.student_id == user.id).order_by(Evidence.created_at).all()
    )

    # Skill cards with confidence; verified means an issuer anchored the
    # document proving this skill and it is not revoked.
    skills: dict[str, dict] = {}
    for evidence in evidences:
        verified_evidence = (
            evidence.credential is not None
            and not evidence.credential.revoked
            and evidence.trust_state == TrustState.VERIFIED.value
        )
        for s in (evidence.extracted or {}).get("skills", []):
            sid = s.get("id")
            if not sid or sid in skills:
                continue
            skills[sid] = {
                "id": sid,
                "name": s.get("name", sid),
                "confidence": s.get("confidence"),
                "verified": verified_evidence or sid in verified_ids,
            }

    credentials: list[dict] = []
    for evidence in evidences:
        cred = evidence.credential
        if cred is None:
            continue
        runs = (
            db.query(AgentRun)
            .filter(AgentRun.evidence_id == evidence.id)
            .order_by(AgentRun.created_at)
            .all()
        )
        credentials.append(
            {
                "id": cred.id,
                "title": evidence.title or evidence.file_name,
                "status": _credential_status(cred, evidence),
                "doc_hash": cred.doc_hash,
                "tx_hash": cred.tx_hash,
                "block_number": cred.block_number,
                "issued_at": cred.issued_at.isoformat() if cred.issued_at else None,
                "revoked": cred.revoked,
                "revoked_at": cred.revoked_at.isoformat() if cred.revoked_at else None,
                "revoke_reason": cred.revoke_reason,
                "issuer_org": cred.issuer.org_name if cred.issuer else "",
                "issuer_address": cred.issuer_address,
                "receipt_path": f"/receipt/{cred.id}?hash={cred.doc_hash}",
                "agent_runs": [agent_run_public(r) for r in runs],
            }
        )

    toggles = user.public_fields or {}
    projects = db.query(Project).filter(Project.student_id == user.id).all()

    return {
        "share_token": user.share_token,
        "student": {
            "full_name": user.full_name if toggles.get("full_name", True) else "",
            "headline": user.headline if toggles.get("headline", True) else "",
            "wallet_address": user.wallet_address,
        },
        "summary": profile_summary(db, user, None).get("summary", ""),
        "skills": sorted(skills.values(), key=lambda s: (-int(s["verified"] or False), str(s["name"]))),
        "credentials": credentials,
        "projects": [project_public(p) for p in projects],
    }


@router.post("/{token}/job-match")
def shared_job_match(token: str, payload: JobMatchRequest, db: Session = Depends(get_db)):
    """Score a pasted job description against the shared profile's
    issuer-verified skills only. Guests never see other candidates."""
    user = _user_by_token(db, token)
    return job_match(db, payload.job_description, payload.role_hint, candidate=user, actor=None)
