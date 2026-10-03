"""Public profiles with per-field privacy toggles (feature 9) and the
Profile Agent summary."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..agents.orchestrator import profile_summary
from ..db import get_db
from ..models import AuditLog, Credential, Evidence, Project, User
from ..schemas import DEFAULT_PUBLIC_FIELDS, ProfileUpdateRequest, project_public, user_public
from ..security import get_current_user
from ..states import TrustState

router = APIRouter(prefix="/api/profile", tags=["profiles"])


@router.get("/me")
def my_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Full private view: everything, plus the Profile Agent summary."""
    summary = profile_summary(db, user, user)
    evidences = (
        db.query(Evidence).filter(Evidence.student_id == user.id).order_by(Evidence.created_at).all()
        if user.role == "student"
        else []
    )
    return {
        "user": user_public(user),
        "summary": summary.get("summary", ""),
        "facts": summary.get("facts", {}),
        "evidence_count": len(evidences),
    }


@router.patch("/me")
def update_profile(
    payload: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.headline is not None:
        user.headline = payload.headline[:500]
    if payload.public_fields is not None:
        # Only known boolean fields are accepted; unknown keys are dropped.
        clean = {
            k: bool(v)
            for k, v in payload.public_fields.items()
            if k in DEFAULT_PUBLIC_FIELDS and isinstance(v, bool)
        }
        # Merged defaults as the base, then apply the user's toggles.
        user.public_fields = {**DEFAULT_PUBLIC_FIELDS, **(user.public_fields or {}), **clean}
    db.add(
        AuditLog(
            id=str(uuid.uuid4()),
            actor_id=user.id,
            actor_role=user.role,
            action="PROFILE_UPDATE",
            object_type="user",
            object_id=user.id,
            detail={"headline": bool(payload.headline), "public_fields": payload.public_fields or {}},
        )
    )
    db.commit()
    return user_public(user)


# Public profile (feature 9): only opted-in fields, no auth required.
public_router = APIRouter(prefix="/api/profiles", tags=["profiles"])


@public_router.get("")
def student_directory(db: Session = Depends(get_db)):
    """Public directory of students, honoring each student's privacy toggles.

    The recruiter search page lists candidates from here; job match then runs
    per candidate id. Only opted-in fields are returned, same as the single
    public profile.
    """
    students = db.query(User).filter(User.role == "student").order_by(User.full_name).all()
    results = []
    for user in students:
        toggles = {**DEFAULT_PUBLIC_FIELDS, **(user.public_fields or {})}
        entry: dict = {
            "user_id": user.id,
            "wallet_address": user.wallet_address,
        }
        if toggles.get("full_name"):
            entry["full_name"] = user.full_name
        if toggles.get("headline"):
            entry["headline"] = user.headline
        if toggles.get("email"):
            entry["email"] = user.email
        if toggles.get("skills"):
            verified, unverified = _split_skills(db, user)
            entry["skills"] = {"verified": sorted(verified), "unverified": sorted(unverified)}
        results.append(entry)
    return results


@public_router.get("/{user_id}")
def public_profile(user_id: str, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    toggles = {**DEFAULT_PUBLIC_FIELDS, **(user.public_fields or {})}
    data: dict = {
        "user_id": user.id,
        "role": user.role,
        "org_name": user.org_name if user.role == "issuer" else "",
        "wallet_address": user.wallet_address,
        "summary": profile_summary(db, user, None).get("summary", "") if user.role == "student" else user.headline,
    }

    if toggles.get("full_name"):
        data["full_name"] = user.full_name
    if toggles.get("headline"):
        data["headline"] = user.headline
    if toggles.get("email"):
        data["email"] = user.email

    if user.role == "student":
        if toggles.get("skills"):
            verified, unverified = _split_skills(db, user)
            data["skills"] = {
                "verified": sorted(verified),
                "unverified": sorted(unverified),
            }
        if toggles.get("projects"):
            projects = db.query(Project).filter(Project.student_id == user.id).all()
            data["projects"] = [project_public(p) for p in projects]
        if toggles.get("credentials"):
            creds = (
                db.query(Credential)
                .join(Evidence, Credential.evidence_id == Evidence.id)
                .filter(Evidence.student_id == user.id)
                .all()
            )
            data["credentials"] = [
                {
                    "id": c.id,
                    "title": c.evidence.title if c.evidence else "",
                    "revoked": c.revoked,
                    "trust_state": (
                        TrustState.ISSUER_VERIFIED.value
                        if not c.revoked
                        else TrustState.REVOKED.value
                    ),
                }
                for c in creds
            ]
    return data


def _split_skills(db: Session, user: User) -> tuple[set[str], set[str]]:
    from ..agents.orchestrator import collect_skill_sets

    return collect_skill_sets(db, user)
