"""Career gap (student) and recruiter job match (feature 4)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..agents.career import load_roles
from ..agents.orchestrator import career_gap, job_match
from ..db import get_db
from ..models import User
from ..schemas import JobMatchRequest
from ..security import get_current_user, require_roles

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
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Recruiter flow: paste a JD, get a score from issuer-verified skills
    only, with unverified skills listed separately and reasoning shown.
    Students can also self-check against a posting."""
    candidate: User = user
    if user.role == "recruiter":
        if not payload.candidate_id:
            raise HTTPException(
                status_code=422, detail="Recruiters must pass candidate_id (the student to match)"
            )
        found = db.get(User, payload.candidate_id)
        if found is None or found.role != "student":
            raise HTTPException(status_code=404, detail="Candidate not found")
        candidate = found
    return job_match(db, payload.job_description, payload.role_hint, candidate)
