"""Phase 3 gate: agents + orchestrator pass with NO API key.

Covers the deterministic fallbacks end to end: evidence extraction, skill
graph mapping, career scoring, integrity verdicts (mocked chain), profile
facts, the LLM wrapper contract (strict JSON, one retry, None on failure)
and AgentRun persistence.
"""

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401  (registers all models on Base.metadata)
from app.db import Base


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    yield session
    session.close()
    engine.dispose()


def make_user(db, role="student", email=None, org=""):
    from app.models import User
    from app.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email=email or f"{role}-{uuid.uuid4().hex[:8]}@agents.test",
        password_hash=hash_password("password-123"),
        full_name="Ananya Sharma" if role == "student" else "Registrar Office",
        role=role,
        org_name=org,
        public_fields={},
        wallet_address="0x000000000000000000000000000000000005tUdE"[:42],
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_evidence(db, student, sha256=None, extracted=None, trust_state="Unverified"):
    from app.models import Evidence

    ev = Evidence(
        id=str(uuid.uuid4()),
        student_id=student.id,
        title="Python Programming",
        file_name="cert.pdf",
        stored_path="/tmp/nonexistent.pdf",
        mime_type="application/pdf",
        file_size=1024,
        sha256=sha256 or uuid.uuid4().hex,
        extracted=extracted or {"skills": [{"id": "python", "name": "Python", "confidence": 0.85}]},
        trust_state=trust_state,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


CERT_TEXT = """Certificate of Completion
This is to certify that
Ananya Sharma
has successfully completed: Python Programming
Awarded by: Springfield College
Date issued: 2026-10-03
Credential ID: ATT-TEST1234
"""


# ---------- LLM wrapper contract (no API key configured here) ----------


def test_llm_offline_by_default():
    from app.agents.llm import chat_json, llm_available

    assert llm_available() is False
    assert chat_json("system", "user", "{}") is None


def _fake_llm(monkeypatch, replies):
    """Swap the http client + settings inside app.agents.llm for a fake."""
    import app.agents.llm as llm_module

    calls = {"n": 0}

    class _Resp:
        def __init__(self, content):
            self._content = content

        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": self._content}}]}

    class _Client:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, url, json=None, headers=None):
            calls["n"] += 1
            idx = min(calls["n"] - 1, len(replies) - 1)
            return _Resp(replies[idx])

    monkeypatch.setattr(llm_module.httpx, "Client", _Client)

    class _Cfg:
        llm_configured = True
        llm_base_url = "http://fake.local"
        llm_model = "test-model"
        llm_api_key = "test-key"

    monkeypatch.setattr(llm_module, "get_settings", lambda: _Cfg())
    return calls


def test_llm_strict_json_retry_recovers_once(monkeypatch):
    from app.agents.llm import chat_json

    calls = _fake_llm(monkeypatch, ["sorry, not json", '{"title": "ok"}'])
    assert chat_json("sys", "user", '{"title": str}') == {"title": "ok"}
    assert calls["n"] == 2  # initial attempt + exactly one retry


def test_llm_gives_up_after_one_retry(monkeypatch):
    from app.agents.llm import chat_json

    calls = _fake_llm(monkeypatch, ["nope", "still nope"])
    assert chat_json("sys", "user", "{}") is None
    assert calls["n"] == 2


def test_evidence_agent_uses_llm_output_when_available(monkeypatch, db):
    import app.agents.evidence as evidence_module
    from app.agents.base import AgentContext
    from app.agents.evidence import EvidenceAgent

    monkeypatch.setattr(evidence_module, "llm_available", lambda: True)
    monkeypatch.setattr(
        evidence_module,
        "chat_json",
        lambda *a, **k: {
            "title": "Intro to Python",
            "issuer": "Springfield College",
            "student_name": "Ananya Sharma",
            "date": "2026-10-03",
            "credential_id": "ATT-LLM0001",
            "skills": ["Python", "Bogus Skill"],
        },
    )
    student = make_user(db)
    ev = make_evidence(db, student, extracted={})
    _run, result = EvidenceAgent().execute(
        AgentContext(db=db, evidence=ev, actor=student, params={"text": CERT_TEXT, "file_name": "c.pdf"})
    )
    assert result.used_fallback is False
    assert result.output["title"] == "Intro to Python"
    # Taxonomy mapping drops unknown skills and keeps known ones.
    assert [s["id"] for s in result.output["skills"]] == ["python"]
    # The run row is persisted for the Agent Trace panel.
    from app.models import AgentRun

    assert db.query(AgentRun).filter(AgentRun.agent == "evidence-verification").count() == 1


# ---------- Evidence Verification Agent (deterministic fallback) ----------


def test_evidence_fallback_extracts_all_fields(db):
    from app.agents.base import AgentContext
    from app.agents.evidence import EvidenceAgent

    _run, result = EvidenceAgent().execute(
        AgentContext(db=db, params={"text": CERT_TEXT, "file_name": "cert.pdf"})
    )
    out = result.output
    assert out["title"] == "Certificate of Completion"
    assert out["issuer"] == "Awarded by: Springfield College"
    assert out["student_name"] == "Ananya Sharma"
    assert out["date"] == "2026-10-03"
    assert out["credential_id"] == "ATT-TEST1234"
    assert [s["id"] for s in out["skills"]] == ["python"]
    assert result.flags == []
    assert result.used_fallback is True
    assert "authentic" not in str(out).lower()  # extraction never claims authenticity


def test_evidence_fallback_flags_missing_and_future_dates(db):
    from app.agents.base import AgentContext
    from app.agents.evidence import EvidenceAgent

    _run, result = EvidenceAgent().execute(
        AgentContext(db=db, params={"text": "Issued on 2099-01-01 somewhere.", "file_name": "x.pdf"})
    )
    assert "suspicious:date-in-future" in result.flags
    assert "missing:student_name" in result.flags
    assert result.confidence < 0.6


# ---------- Skill Graph Agent ----------


def test_skill_graph_maps_taxonomy_with_strength(db):
    from app.agents.base import AgentContext
    from app.agents.skills import SkillGraphAgent

    student = make_user(db)
    ev = make_evidence(
        db,
        student,
        extracted={"skills": [{"id": "python", "name": "Python", "confidence": 0.9}]},
    )
    _run, result = SkillGraphAgent().execute(AgentContext(db=db, evidence=ev))
    assert result.output["skills"][0]["id"] == "python"
    assert result.output["edges"] == [{"from": ev.id, "to": "python", "strength": 0.9}]
    assert result.flags == []


def test_skill_graph_flags_when_nothing_maps(db):
    from app.agents.base import AgentContext
    from app.agents.skills import SkillGraphAgent

    student = make_user(db)
    ev = make_evidence(db, student, extracted={"skills": [{"id": "nope", "name": "Nope"}]})
    _run, result = SkillGraphAgent().execute(AgentContext(db=db, evidence=ev))
    assert result.flags == ["no-skills-mapped"]


# ---------- Career Mentor Agent ----------


def test_score_skills_weights_verified_above_unverified():
    from app.agents.career import score_skills

    required = [
        {"skill_id": "python", "weight": 0.9},
        {"skill_id": "sql", "weight": 0.95},
        {"skill_id": "excel", "weight": 0.8},
    ]
    score, matched, missing, unverified = score_skills(required, {"python"}, {"sql"})
    # python full (0.9) + sql at 40 percent (0.38) over 2.65 total.
    assert score == round((0.9 + 0.95 * 0.4) / 2.65 * 100)
    assert [m["skill_id"] for m in matched] == ["python"]
    assert [u["skill_id"] for u in unverified] == ["sql"]
    assert [m["skill_id"] for m in missing] == ["excel"]


def test_career_mentor_priorities_and_project_ideas(db):
    from app.agents.base import AgentContext
    from app.agents.career import CareerMentorAgent, get_role, priority_for

    assert priority_for(0.95, 0.95) == "High"
    assert priority_for(0.7, 0.95) == "Medium"
    assert priority_for(0.4, 0.95) == "Low"
    assert get_role(None)["id"] == "data-analyst"  # default target role
    assert get_role("blockchain-developer")["title"] == "Blockchain Developer"

    _run, result = CareerMentorAgent().execute(
        AgentContext(db=db, params={"verified_skills": ["python"], "unverified_skills": []})
    )
    out = result.output
    assert out["role"]["id"] == "data-analyst"
    assert len(out["project_ideas"]) == 3
    assert any(m["skill_id"] == "sql" for m in out["missing"] if m["priority"] == "High")
    assert "python" in [m["skill_id"] for m in out["matched"]]
    assert result.flags == []


def test_career_mentor_flags_no_verified_skills(db):
    from app.agents.base import AgentContext
    from app.agents.career import CareerMentorAgent

    _run, result = CareerMentorAgent().execute(
        AgentContext(db=db, params={"verified_skills": [], "unverified_skills": ["excel"]})
    )
    assert result.flags == ["no-verified-skills"]
    assert any(u["skill_id"] == "excel" for u in result.output["unverified"])


# ---------- Integrity Agent (deterministic, mocked chain) ----------


def _make_cred(db, evidence, issuer):
    from app.models import Credential

    cred = Credential(
        id=str(uuid.uuid4()),
        chain_credential_id="0x" + f"{1:064x}",
        evidence_id=evidence.id,
        issuer_id=issuer.id,
        recipient_address=evidence.student.wallet_address,
        doc_hash=evidence.sha256,
        tx_hash="0x" + f"{2:064x}",
        block_number=5,
    )
    db.add(cred)
    db.commit()
    db.refresh(cred)
    return cred


def _patch_chain(monkeypatch, status=None, record=None, error=None):
    from app import chain as chain_module

    def verify(cid, presented):
        if error:
            raise chain_module.ChainError(error)
        return status

    def get(cid):
        if error:
            raise chain_module.ChainError(error)
        return record

    monkeypatch.setattr(chain_module, "verify_onchain", verify)
    monkeypatch.setattr(chain_module, "get_onchain_credential", get)


_RECORD = {
    "doc_hash": None,  # set per test to the evidence hash
    "issuer": "0xIssuer",
    "recipient": "0xRecipient",
    "issued_at": 1700000000,
    "revoked_at": 0,
    "revoke_reason": "",
    "revoked": False,
    "exists": True,
}


@pytest.mark.parametrize(
    "status,expected_state",
    [
        (1, "Verified"),
        (2, "Tampered"),
        (3, "Revoked"),
    ],
)
def test_integrity_verdicts_from_chain_status(monkeypatch, db, status, expected_state):
    from app.agents.base import AgentContext
    from app.agents.integrity import IntegrityAgent

    student = make_user(db)
    issuer = make_user(db, role="issuer", org="Springfield College")
    sha = uuid.uuid4().hex
    ev = make_evidence(db, student, sha256=sha)
    cred = _make_cred(db, ev, issuer)

    record = {**_RECORD, "doc_hash": "0x" + sha, "revoked": status == 3, "revoke_reason": "demo" if status == 3 else ""}
    _patch_chain(monkeypatch, status=status, record=record)

    _run, result = IntegrityAgent().execute(
        AgentContext(db=db, evidence=ev, params={"credential": cred})
    )
    assert result.output["trust_state"] == expected_state
    assert result.output["hash_match"] is True
    assert result.confidence == 1.0
    if expected_state == "Revoked":
        assert "demo" in result.output["reason"]


def test_integrity_tampered_when_hash_mismatch(monkeypatch, db):
    from app.agents.base import AgentContext
    from app.agents.integrity import IntegrityAgent

    student = make_user(db)
    issuer = make_user(db, role="issuer", org="College")
    ev = make_evidence(db, student)
    cred = _make_cred(db, ev, issuer)
    record = {**_RECORD, "doc_hash": "0x" + "f" * 64}
    _patch_chain(monkeypatch, status=2, record=record)

    _run, result = IntegrityAgent().execute(
        AgentContext(db=db, evidence=ev, params={"credential": cred})
    )
    assert result.output["trust_state"] == "Tampered"
    assert result.output["hash_match"] is False


def test_integrity_no_credential_is_unknown_not_verified(db):
    from app.agents.base import AgentContext
    from app.agents.integrity import IntegrityAgent

    student = make_user(db)
    ev = make_evidence(db, student)
    _run, result = IntegrityAgent().execute(AgentContext(db=db, evidence=ev))
    assert result.output["trust_state"] == "Not found"
    assert "no-credential" in result.flags


def test_integrity_chain_outage_never_invents_a_verdict(monkeypatch, db):
    from app.agents.base import AgentContext
    from app.agents.integrity import IntegrityAgent

    student = make_user(db)
    issuer = make_user(db, role="issuer", org="College")
    ev = make_evidence(db, student)
    cred = _make_cred(db, ev, issuer)
    _patch_chain(monkeypatch, error="node down")

    _run, result = IntegrityAgent().execute(
        AgentContext(db=db, evidence=ev, params={"credential": cred})
    )
    assert "chain-unavailable" in result.flags
    assert "trust_state" not in result.output  # caller keeps the previous state


# ---------- Profile Agent ----------


def test_profile_agent_summarizes_only_facts(db):
    from app.agents.base import AgentContext
    from app.agents.profile import ProfileAgent

    student = make_user(db)
    facts = {
        "verified_skills": ["python", "sql"],
        "unverified_skills": ["docker"],
        "credentials": [{"id": "c1", "title": "Python Programming"}],
        "projects": [{"id": "p1", "title": "Sales dashboard"}],
    }
    _run, result = ProfileAgent().execute(
        AgentContext(db=db, actor=student, params={"user": student, "facts": facts})
    )
    summary = result.output["summary"]
    assert "Ananya Sharma" in summary
    assert "python, sql" in summary
    assert "Verified credentials on-chain: 1" in summary
    assert "Sales dashboard" in summary


# ---------- Orchestrator ----------


def test_orchestrator_analyze_on_real_pdf(db, tmp_path):
    from app.agents.orchestrator import analyze_evidence
    from app.models import Evidence
    from app.services.sample_docs import write_sample_certificate_pdf

    student = make_user(db)
    path, sha = write_sample_certificate_pdf(
        student, "Python Programming", "Springfield College", out_dir=str(tmp_path)
    )
    ev = Evidence(
        id=str(uuid.uuid4()),
        student_id=student.id,
        title="",
        file_name="python-cert.pdf",
        stored_path=path,
        mime_type="application/pdf",
        file_size=1,
        sha256=sha,
        extracted={},
        trust_state="Unverified",
    )
    db.add(ev)
    db.commit()

    analyze_evidence(db, ev, student)
    assert ev.extracted["title"] == "Certificate of Completion"
    assert ev.extracted["student_name"] == "Ananya Sharma"
    assert "python" in [s["id"] for s in ev.extracted["skills"]]
    assert ev.title  # fallback title promotion


def test_collect_skill_sets_verified_wins_and_projects_are_unverified(db):
    from app.agents.orchestrator import collect_skill_sets
    from app.models import Project

    student = make_user(db)
    issuer = make_user(db, role="issuer", org="College")

    verified_ev = make_evidence(
        db, student, trust_state="Verified",
        extracted={"skills": [{"id": "python", "name": "Python", "confidence": 0.9}]},
    )
    _make_cred(db, verified_ev, issuer)

    unverified_ev = make_evidence(
        db, student, trust_state="Unverified",
        extracted={"skills": [{"id": "sql", "name": "SQL", "confidence": 0.9}]},
    )
    assert unverified_ev is not None

    project = Project(
        id=str(uuid.uuid4()), student_id=student.id, title="Dash", description="", skills=["excel"]
    )
    db.add(project)
    db.commit()

    verified, unverified = collect_skill_sets(db, student)
    assert verified == {"python"}
    assert unverified == {"sql", "excel"}


def test_build_graph_nodes_edges_and_verified_flags(db):
    from app.agents.orchestrator import build_graph
    from app.models import Project

    student = make_user(db)
    issuer = make_user(db, role="issuer", org="College")
    verified_ev = make_evidence(
        db, student, trust_state="Verified",
        extracted={"skills": [{"id": "python", "name": "Python", "confidence": 0.9}]},
    )
    _make_cred(db, verified_ev, issuer)
    db.add(Project(id=str(uuid.uuid4()), student_id=student.id, title="ETL", skills=["sql"]))
    db.commit()

    graph = build_graph(db, student)
    kinds = {n["kind"] for n in graph["nodes"]}
    assert kinds == {"evidence", "skill", "project"}
    skill_flags = {n["id"]: n["verified"] for n in graph["nodes"] if n["kind"] == "skill"}
    assert skill_flags["python"] is True  # anchored + verified evidence
    assert skill_flags["sql"] is False  # from a project, unverified
    edge_kinds = {e["kind"] for e in graph["edges"]}
    assert edge_kinds == {"evidence-skill", "project-skill"}
    assert all(0 <= e["strength"] <= 1 for e in graph["edges"])


def test_job_match_scores_verified_skills_only(db):
    from app.agents.orchestrator import job_match

    student = make_user(db)
    issuer = make_user(db, role="issuer", org="College")
    verified_ev = make_evidence(
        db, student, trust_state="Verified",
        extracted={"skills": [{"id": "python", "name": "Python", "confidence": 0.9}]},
    )
    _make_cred(db, verified_ev, issuer)
    make_evidence(
        db, student, trust_state="Unverified",
        extracted={"skills": [{"id": "sql", "name": "SQL", "confidence": 0.9}]},
    )

    jd = "We are hiring an analyst with strong Python and SQL skills for reporting."
    out = job_match(db, jd, "data-analyst", student)

    assert out["matched"] and out["matched"][0]["skill_id"] == "python"
    assert any(u["skill_id"] == "sql" for u in out["unverified"])
    assert out["score"] > 0
    # sql appears only as unverified: it must not be in the matched list.
    assert "sql" not in [m["skill_id"] for m in out["matched"]]
    assert "reasoning" in out and out["run_id"]
    from app.models import AgentRun

    run = db.get(AgentRun, out["run_id"])
    assert run is not None and run.agent == "career-mentor" and run.evidence_id is None


def test_job_match_with_no_taxonomy_hits_flags_low_confidence(db):
    from app.agents.orchestrator import job_match

    student = make_user(db)
    out = job_match(db, "Walking the dog and watering plants.", None, student)
    assert out["score"] == 0
    assert out["required_count"] == 0
