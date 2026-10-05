"""Orchestrator: the only entry point the routers use to run agents.

Responsibilities:
- run agent pipelines in order and persist AgentRun rows (via BaseAgent.execute)
- write evidence extraction results back to the evidence row
- apply Integrity Agent verdicts to the trust state (only place this happens)
- collect verified/unverified skill sets for career + job match
"""

import uuid

from sqlalchemy.orm import Session

from ..models import AgentRun, AuditLog, Credential, Evidence, Project, User
from ..services.extraction import extract_text
from ..states import TrustState
from .base import AgentContext
from .career import CareerMentorAgent
from .evidence import EvidenceAgent
from .integrity import IntegrityAgent
from .profile import ProfileAgent
from .skills import SkillGraphAgent


def _audit(db: Session, actor: User | None, action: str, object_type: str, object_id: str, detail: dict) -> None:
    db.add(
        AuditLog(
            id=str(uuid.uuid4()),
            actor_id=actor.id if actor else "",
            actor_role=actor.role if actor else "",
            action=action,
            object_type=object_type,
            object_id=object_id,
            detail=detail,
        )
    )


def analyze_evidence(db: Session, evidence: Evidence, actor: User | None) -> Evidence:
    """Run Evidence Verification + Skill Graph for a freshly uploaded file."""
    text, warnings = extract_text(evidence.stored_path, evidence.mime_type)
    evidence.extracted = {"warnings": warnings}

    ctx = AgentContext(
        db=db,
        evidence=evidence,
        actor=actor,
        params={"text": text, "file_name": evidence.file_name},
    )
    _, ev_result = EvidenceAgent().execute(ctx)
    evidence.extracted = {
        "warnings": warnings,
        "title": ev_result.output.get("title", ""),
        "issuer": ev_result.output.get("issuer", ""),
        "student_name": ev_result.output.get("student_name", ""),
        "date": ev_result.output.get("date", ""),
        "credential_id": ev_result.output.get("credential_id", ""),
        "skills": ev_result.output.get("skills", []),
        "confidence": ev_result.confidence,
        "flags": ev_result.flags,
    }
    if not evidence.title and ev_result.output.get("title"):
        evidence.title = ev_result.output["title"][:300]

    SkillGraphAgent().execute(AgentContext(db=db, evidence=evidence, actor=actor))
    db.commit()
    return evidence


def verify_evidence(
    db: Session,
    evidence: Evidence,
    actor: User | None,
    presented_sha256: str | None = None,
) -> dict:
    """Run the Integrity Agent and apply its verdict to the evidence row."""
    credential: Credential | None = evidence.credential
    ctx = AgentContext(
        db=db,
        evidence=evidence,
        actor=actor,
        params={"presented_sha256": presented_sha256, "credential": credential},
    )
    _, result = IntegrityAgent().execute(ctx)
    output = result.output

    state = output.get("trust_state")
    if state == TrustState.VERIFIED.value:
        evidence.trust_state = TrustState.VERIFIED.value
    elif state == TrustState.REVOKED.value:
        evidence.trust_state = TrustState.REVOKED.value
    elif state == TrustState.TAMPERED.value:
        evidence.trust_state = TrustState.TAMPERED.value
    elif state == TrustState.NOT_FOUND.value and "chain-record-missing" in result.flags:
        # On-chain record vanished (chain reset): drop back to unverified.
        evidence.trust_state = TrustState.UNVERIFIED.value

    _audit(
        db,
        actor,
        "VERIFY",
        "evidence",
        evidence.id,
        {"trust_state": output.get("trust_state"), "presented_hash": (presented_sha256 or evidence.sha256)},
    )
    db.commit()
    return output


def collect_skill_sets(db: Session, user: User) -> tuple[set[str], set[str]]:
    """(verified, unverified) skill ids across evidence + projects."""
    verified: set[str] = set()
    unverified: set[str] = set()
    evidences = db.query(Evidence).filter(Evidence.student_id == user.id).all()
    for ev in evidences:
        ids = [s.get("id") for s in (ev.extracted or {}).get("skills", []) if s.get("id")]
        is_verified = (
            ev.credential is not None
            and not ev.credential.revoked
            and ev.trust_state == TrustState.VERIFIED.value
        )
        (verified if is_verified else unverified).update(ids)
    for project in db.query(Project).filter(Project.student_id == user.id).all():
        unverified.update(project.skills or [])
    # Verified wins when a skill appears in both sets.
    return verified, unverified - verified


def career_gap(db: Session, user: User, role_id: str | None, actor: User | None) -> dict:
    verified, unverified = collect_skill_sets(db, user)
    ctx = AgentContext(
        db=db,
        actor=actor,
        params={
            "verified_skills": list(verified),
            "unverified_skills": list(unverified),
            "role_id": role_id,
        },
    )
    _, result = CareerMentorAgent().execute(ctx)
    db.commit()
    return result.output


def job_match(
    db: Session,
    jd_text: str,
    role_hint: str | None,
    candidate: User,
    actor: User | None = None,
) -> dict:
    """Score a pasted job description using issuer-verified skills only.
    `candidate` owns the skills; `actor` (when logged in) is audited."""
    from .career import get_role, score_skills  # reuse the exact scoring (avoids cycle)
    from .evidence import load_taxonomy

    taxonomy = load_taxonomy()
    lower = jd_text.lower()
    required: list[dict] = []

    # Role weights take precedence for skills that overlap the hinted role.
    role_weights: dict[str, float] = {}
    if role_hint:
        try:
            role = get_role(role_hint)
            role_weights = {r["skill_id"]: r["weight"] for r in role["required_skills"]}
        except Exception:
            role_weights = {}

    for key, skill in taxonomy.items():
        if key and f" {key} " in f" {lower} ".replace("\n", " "):
            weight = role_weights.get(skill["id"], 0.9)
            if skill["id"] not in [r["skill_id"] for r in required]:
                required.append({"skill_id": skill["id"], "weight": weight})

    # Alias matches count a bit lower than direct name matches.
    verified, unverified = collect_skill_sets(db, candidate)

    pseudo_role = {
        "id": role_hint or "job-description",
        "title": "Pasted job description",
        "required_skills": required,
    }
    score, matched, missing, unverified_list = score_skills(required, verified, unverified)
    reasoning_parts = []
    verified_matched = [m["skill_id"] for m in matched]
    reasoning_parts.append(
        f"The job description mentions {len(required)} skills from the taxonomy. "
        f"Score {score}/100 counts issuer-verified skills only: "
        f"{', '.join(verified_matched) if verified_matched else 'none verified yet'}."
    )
    if unverified_list:
        reasoning_parts.append(
            "Unverified matches (not counted in the score): "
            + ", ".join(u["skill_id"] for u in unverified_list)
            + "."
        )
    if missing:
        reasoning_parts.append(
            "Missing from this candidate: " + ", ".join(m["skill_id"] for m in missing[:5]) + "."
        )

    # Persist the run for the Agent Trace panel (evidence_id is null here).
    agent = CareerMentorAgent()
    run_row = AgentRun(
        id=str(uuid.uuid4()),
        evidence_id=None,
        agent=agent.name,
        input_summary=f"job match: {len(required)} taxonomy skills, hint={role_hint or 'none'}",
        output={
            "role": {"id": pseudo_role["id"], "title": pseudo_role["title"]},
            "score": score,
            "matched": matched,
            "missing": missing,
            "unverified": unverified_list,
            "reasoning": " ".join(reasoning_parts),
        },
        confidence=0.8 if required else 0.3,
        flags=[] if required else ["no-taxonomy-match-in-jd"],
        duration_ms=0,
        used_fallback=True,
    )
    db.add(run_row)
    _audit(db, actor, "AGENT_RUN", "job-match", "", {"agent": agent.name, "score": score})
    db.commit()

    return {
        "score": score,
        "matched": matched,
        "missing": missing,
        "unverified": unverified_list,
        "required_count": len(required),
        "reasoning": " ".join(reasoning_parts),
        "run_id": run_row.id,
    }


def build_graph(db: Session, user: User) -> dict:
    """Nodes and edges for the skill graph page. Verified/unverified is a
    flag on each node; the frontend differentiates by border style + label,
    never by color alone."""
    evidences = (
        db.query(Evidence).filter(Evidence.student_id == user.id).order_by(Evidence.created_at).all()
    )
    projects = db.query(Project).filter(Project.student_id == user.id).all()

    nodes: list[dict] = []
    edges: list[dict] = []

    for ev in evidences:
        verified = (
            ev.credential is not None
            and not ev.credential.revoked
            and ev.trust_state == TrustState.VERIFIED.value
        )
        nodes.append(
            {
                "id": ev.id,
                "kind": "evidence",
                "label": ev.title or ev.file_name,
                "trust_state": ev.trust_state,
                "verified": verified,
            }
        )
        for skill in (ev.extracted or {}).get("skills", []):
            sid = skill.get("id")
            if not sid:
                continue
            skill_verified = verified
            if not any(n["id"] == sid for n in nodes if n["kind"] == "skill"):
                nodes.append(
                    {
                        "id": sid,
                        "kind": "skill",
                        "label": skill.get("name", sid),
                        "category": skill.get("category", ""),
                        "verified": skill_verified,
                    }
                )
            else:
                # A skill is verified if ANY evidence proving it is verified.
                existing = next(n for n in nodes if n["id"] == sid and n["kind"] == "skill")
                existing["verified"] = existing["verified"] or skill_verified
            edges.append({"from": ev.id, "to": sid, "kind": "evidence-skill", "strength": skill.get("confidence", 0.5)})

    for project in projects:
        nodes.append(
            {
                "id": project.id,
                "kind": "project",
                "label": project.title,
                "trust_state": TrustState.UNVERIFIED.value,
                "verified": False,
            }
        )
        for sid in project.skills or []:
            if not any(n["id"] == sid for n in nodes if n["kind"] == "skill"):
                nodes.append(
                    {"id": sid, "kind": "skill", "label": sid, "category": "", "verified": False}
                )
            edges.append({"from": project.id, "to": sid, "kind": "project-skill", "strength": 0.6})

    return {"nodes": nodes, "edges": edges}


def profile_summary(db: Session, user: User, actor: User | None) -> dict:
    verified, unverified = collect_skill_sets(db, user)
    creds = (
        db.query(Credential)
        .join(Evidence, Credential.evidence_id == Evidence.id)
        .filter(Evidence.student_id == user.id, Credential.revoked.is_(False))
        .all()
    )
    projects = db.query(Project).filter(Project.student_id == user.id).all()
    facts = {
        "verified_skills": sorted(verified),
        "unverified_skills": sorted(unverified),
        "credentials": [{"id": c.id, "title": c.evidence.title} for c in creds],
        "projects": [{"id": p.id, "title": p.title} for p in projects],
    }
    ctx = AgentContext(db=db, actor=actor, params={"user": user, "facts": facts})
    _, result = ProfileAgent().execute(ctx)
    db.commit()
    return {**result.output, "facts": facts}
