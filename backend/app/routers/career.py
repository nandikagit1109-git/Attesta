"""Career gap (student) and recruiter job match (feature 4)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..agents.career import load_roles
from ..agents.orchestrator import career_gap, job_match
from ..db import get_db
from ..models import User
from ..schemas import JobMatchRequest
from ..security import require_roles

router = APIRouter(prefix="/api/career", tags=["career"])


@router.get("/roles")
def roles():
    data = load_roles()
    return {
        "roles": [
            {"id": r["id"], "title": r["title"], "description": r["description"]}
            for r in data["roles"]
        ],
        "default": data.get("default_target_role_id"),
    }


@router.get("/gap")
def gap(
    role: str | None = None,
    user: User = Depends(require_roles("student")),
    db: Session = Depends(get_db),
):
    """Missing skills vs a target role; verified skills count above
    unverified ones; three project ideas included."""
    return career_gap(db, user, role, user)


@router.post("/job-match")
def job_match_endpoint(
    payload: JobMatchRequest,
    user: User = Depends(require_roles("student")),
    db: Session = Depends(get_db),
):
    """Student self-check: paste a JD, get a score from issuer-verified
    skills only, with unverified skills listed separately. Guests use the
    share-link variant /api/share/{token}/job-match instead."""
    return job_match(db, payload.job_description, payload.role_hint, candidate=user, actor=user)
