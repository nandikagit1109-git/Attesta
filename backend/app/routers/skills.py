"""Skill graph (feature 6) and student projects."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..agents.orchestrator import build_graph
from ..db import get_db
from ..models import Project, User
from ..schemas import ProjectCreateRequest, project_public
from ..security import get_current_user, require_roles

router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.get("/graph")
def skill_graph(user: User = Depends(require_roles("student")), db: Session = Depends(get_db)):
    """Nodes/edges for the React Flow graph. The `verified` flag on each node
    drives border style + label in the UI (never color alone)."""
    return build_graph(db, user)


@router.get("/taxonomy")
def taxonomy():
    """The standard taxonomy, for dropdowns and job-match hints."""
    from ..agents.evidence import load_taxonomy

    seen = {}
    for skill in load_taxonomy().values():
        seen[skill["id"]] = {
            "id": skill["id"],
            "name": skill["name"],
            "category": skill["category"],
        }
    return {"skills": sorted(seen.values(), key=lambda s: (s["category"], s["name"]))}


# Projects (used by the graph and the career gap page)

projects_router = APIRouter(prefix="/api/projects", tags=["projects"])


@projects_router.post("")
def create_project(
    payload: ProjectCreateRequest,
    user: User = Depends(require_roles("student")),
    db: Session = Depends(get_db),
):
    project = Project(
        id=str(uuid.uuid4()),
        student_id=user.id,
        title=payload.title,
        description=payload.description,
        skills=payload.skills,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project_public(project)


@projects_router.get("")
def list_projects(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Project)
    if user.role == "student":
        query = query.filter(Project.student_id == user.id)
    return [project_public(p) for p in query.order_by(Project.created_at).all()]


@projects_router.delete("/{project_id}")
def delete_project(
    project_id: str,
    user: User = Depends(require_roles("student")),
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.student_id != user.id:
        raise HTTPException(status_code=403, detail="Not your project")
    db.delete(project)
    db.commit()
    return {"deleted": project_id}
