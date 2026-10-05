"""Own profile with per-field privacy toggles and the Profile Agent summary.

The old public profiles directory was removed deliberately (revised spec):
recruiters are guests and must not be able to enumerate students. The only
public door is the student's own share token under /api/share/{token}.
"""

import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..agents.orchestrator import profile_summary
from ..db import get_db
from ..models import AuditLog, Evidence, User
from ..schemas import DEFAULT_PUBLIC_FIELDS, ProfileUpdateRequest, user_public
from ..security import get_current_user

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


@router.post("/share-link")
def create_share_link(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create (or return) the student's guest share token. Recruiters open
    /s/{token} or scan its QR — no account, no directory, no enumeration."""
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Only students publish share links")
    if not user.share_token:
        user.share_token = secrets.token_urlsafe(24)
        db.add(
            AuditLog(
                id=str(uuid.uuid4()),
                actor_id=user.id,
                actor_role=user.role,
                action="SHARE_LINK",
                object_type="user",
                object_id=user.id,
                detail={},
            )
        )
        db.commit()
        db.refresh(user)
    return {"share_token": user.share_token, "share_path": f"/s/{user.share_token}"}
