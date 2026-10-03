"""Pydantic request models and response serializers.

Responses are built as plain dicts by the serializer helpers so nested data
(student, credential, agent runs) stays explicit and OpenAPI documents it via
response models where used.
"""

from typing import Any

from pydantic import BaseModel, EmailStr, Field

from .models import AgentRun, Credential, Evidence, Project, User

# ---------- Requests ----------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    role: str = Field(pattern="^(student|issuer|recruiter)$")
    org_name: str = Field(default="", max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class ProfileUpdateRequest(BaseModel):
    headline: str | None = Field(default=None, max_length=500)
    public_fields: dict[str, bool] | None = None


class ProjectCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(default="", max_length=4000)
    skills: list[str] = Field(default_factory=list, max_length=30)


class IssueRequest(BaseModel):
    evidence_id: str


class RevokeRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=300)


class VerifyHashRequest(BaseModel):
    sha256: str = Field(pattern="^[0-9a-fA-F]{64}$")
    credential_id: str | None = None


class JobMatchRequest(BaseModel):
    job_description: str = Field(min_length=10, max_length=8000)
    role_hint: str | None = Field(default=None, max_length=120)
    # Recruiters match against a candidate; students match themselves.
    candidate_id: str | None = None


# ---------- Serializers ----------

DEFAULT_PUBLIC_FIELDS = {
    "full_name": True,
    "headline": True,
    "skills": True,
    "projects": True,
    "credentials": True,
    "email": False,
}


def user_public(u: User) -> dict[str, Any]:
    return {
        "id": u.id,
        "email": u.email,
        "full_name": u.full_name,
        "role": u.role,
        "org_name": u.org_name,
        "headline": u.headline,
        "wallet_address": u.wallet_address,
        "public_fields": {**DEFAULT_PUBLIC_FIELDS, **(u.public_fields or {})},
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


def agent_run_public(r: AgentRun) -> dict[str, Any]:
    return {
        "id": r.id,
        "agent": r.agent,
        "input_summary": r.input_summary,
        "output": r.output,
        "confidence": r.confidence,
        "flags": r.flags or [],
        "duration_ms": r.duration_ms,
        "used_fallback": r.used_fallback,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def credential_public(c: Credential) -> dict[str, Any]:
    return {
        "id": c.id,
        "chain_credential_id": c.chain_credential_id,
        "evidence_id": c.evidence_id,
        "issuer_id": c.issuer_id,
        "issuer_name": c.issuer.full_name if c.issuer else "",
        "issuer_org": c.issuer.org_name if c.issuer else "",
        "recipient_address": c.recipient_address,
        "doc_hash": c.doc_hash,
        "tx_hash": c.tx_hash,
        "block_number": c.block_number,
        "revoked": c.revoked,
        "revoked_at": c.revoked_at.isoformat() if c.revoked_at else None,
        "revoke_reason": c.revoke_reason,
        "issued_at": c.issued_at.isoformat() if c.issued_at else None,
    }


def evidence_public(
    e: Evidence,
    include_runs: bool = False,
    db: Any = None,
) -> dict[str, Any]:
    """Serialize evidence. Skill verified-ness derives from its credential:
    a skill is verified only when the evidence has an Issuer-verified,
    non-revoked credential."""
    from .states import TrustState

    student = e.student
    cred = e.credential
    verified_skills: set[str] = set()
    if cred and not cred.revoked and e.trust_state == TrustState.ISSUER_VERIFIED.value:
        for s in (e.extracted or {}).get("skills", []):
            if s.get("id"):
                verified_skills.add(s["id"])

    data: dict[str, Any] = {
        "id": e.id,
        "title": e.title,
        "file_name": e.file_name,
        "mime_type": e.mime_type,
        "file_size": e.file_size,
        "sha256": e.sha256,
        "trust_state": e.trust_state,
        "extracted": e.extracted or {},
        "skills": [
            {**s, "verified": s.get("id") in verified_skills}
            for s in (e.extracted or {}).get("skills", [])
        ],
        "student": {"id": student.id, "full_name": student.full_name} if student else None,
        "credential": credential_public(cred) if cred else None,
        "has_tampered_copy": bool(e.tampered_copy_path),
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }
    if include_runs and db is not None:
        runs = (
            db.query(AgentRun)
            .filter(AgentRun.evidence_id == e.id)
            .order_by(AgentRun.created_at)
            .all()
        )
        data["agent_runs"] = [agent_run_public(r) for r in runs]
    return data


def project_public(p: Project) -> dict[str, Any]:
    return {
        "id": p.id,
        "title": p.title,
        "description": p.description,
        "skills": p.skills or [],
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


def audit_public(row: Any) -> dict[str, Any]:
    return {
        "id": row.id,
        "actor_id": row.actor_id,
        "actor_role": row.actor_role,
        "action": row.action,
        "object_type": row.object_type,
        "object_id": row.object_id,
        "detail": row.detail or {},
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
