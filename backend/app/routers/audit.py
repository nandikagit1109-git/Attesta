"""Read access to the audit trail (feature 10).

Every issue, revoke, verify and agent run is written by the routers and the
agent framework; this endpoint exposes the trail. Students see their own
entries only; issuers and recruiters see the full trail.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import AuditLog, User
from ..schemas import audit_public
from ..security import get_current_user

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("")
def list_audit(
    limit: int = Query(default=100, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(AuditLog)
    if user.role == "student":
        query = query.filter(AuditLog.actor_id == user.id)
    rows = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
    return [audit_public(r) for r in rows]
