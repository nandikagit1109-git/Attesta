"""Evidence API: upload + agent analysis, listing, permissions, tamper demo,
verification without a credential, and upload validation."""

import hashlib

from tests.conftest import demo_login, pdf_bytes, register


def _upload(client, headers, title="Python Programming", name="python-cert.pdf", content=None):
    return client.post(
        "/api/evidence",
        headers=headers,
        files={"file": (name, content if content is not None else pdf_bytes(), "application/pdf")},
        data={"title": title},
    )


def test_upload_runs_agents_and_stays_unverified(client):
    headers, _user = demo_login(client, "student")
    resp = _upload(client, headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # Trust model: fresh evidence is AI-extracted (unverified), never proof.
    assert body["trust_state"] == "AI-extracted (unverified)"

    ex = body["extracted"]
    assert ex["title"] == "Certificate of Completion"  # extraction reads the document itself
    assert "Springfield College" in ex["issuer"]
    assert ex["student_name"] == "Ananya Sharma"
    assert ex["date"]  # date parsed from the certificate
    assert ex["credential_id"].startswith("ATT-")
    skill_ids = [s["id"] for s in ex["skills"]]
    assert "python" in skill_ids  # deterministic fallback found the taxonomy skill

    # Agent Trace (feature 2): evidence + skill-graph runs with timing + fallback flag.
    agents = {r["agent"]: r for r in body["agent_runs"]}
    assert "evidence-verification" in agents and "skill-graph" in agents
    assert agents["evidence-verification"]["used_fallback"] is True
    assert agents["evidence-verification"]["duration_ms"] >= 0
    assert agents["evidence-verification"]["confidence"] > 0


def test_uploaded_hash_matches_browser_side_sha256(client):
    headers, _ = demo_login(client, "student")
    content = pdf_bytes()
    resp = _upload(client, headers, content=content)
    assert resp.json()["sha256"] == hashlib.sha256(content).hexdigest()


def test_student_sees_only_own_evidence_others_cannot_read(client):
    student_headers, _ = demo_login(client, "student")
    other_headers, _ = register(client, "other-student@test.dev")
    issuer_headers, _ = demo_login(client, "issuer")
    recruiter_headers, _ = demo_login(client, "recruiter")

    created = _upload(client, student_headers).json()
    eid = created["id"]

    listed = client.get("/api/evidence", headers=student_headers).json()
    assert [e["id"] for e in listed] == [eid]

    assert client.get(f"/api/evidence/{eid}", headers=other_headers).status_code == 403
    assert client.get(f"/api/evidence/{eid}", headers=issuer_headers).status_code == 200
    assert client.get(f"/api/evidence/{eid}", headers=recruiter_headers).status_code == 200


def test_tamper_creates_one_byte_flipped_copy(client):
    headers, _ = demo_login(client, "student")
    evidence = _upload(client, headers).json()

    tamper = client.post(f"/api/evidence/{evidence['id']}/tamper", headers=headers)
    assert tamper.status_code == 200
    body = tamper.json()
    assert body["tampered_sha256"] != body["original_sha256"]

    # The downloaded tampered copy really hashes to the reported value.
    download = client.get(f"/api/evidence/{evidence['id']}/tamper-file", headers=headers)
    assert download.status_code == 200
    assert hashlib.sha256(download.content).hexdigest() == body["tampered_sha256"]

    # Idempotent: a second tamper call reuses the same copy.
    again = client.post(f"/api/evidence/{evidence['id']}/tamper", headers=headers)
    assert again.json()["tampered_sha256"] == body["tampered_sha256"]


def test_tamper_blocked_for_other_students(client):
    owner_headers, _ = demo_login(client, "student")
    other_headers, _ = register(client, "no-tamper@test.dev")
    evidence = _upload(client, owner_headers).json()
    resp = client.post(f"/api/evidence/{evidence['id']}/tamper", headers=other_headers)
    assert resp.status_code == 403


def test_verify_without_credential_stays_unverified(client):
    """The Integrity Agent must not invent a verdict when nothing is on-chain."""
    headers, _ = demo_login(client, "student")
    evidence = _upload(client, headers).json()

    resp = client.post(f"/api/evidence/{evidence['id']}/verify", headers=headers)
    assert resp.status_code == 200
    verification = resp.json()["verification"]
    assert verification["trust_state"] == "Unknown"
    assert "no-credential" in verification.get("flags", []) or verification.get("reason")
    # The evidence keeps its honest unverified state.
    assert resp.json()["evidence"]["trust_state"] == "AI-extracted (unverified)"


def test_upload_rejects_bad_type_and_empty_file(client):
    headers, _ = demo_login(client, "student")

    bad_type = client.post(
        "/api/evidence",
        headers=headers,
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert bad_type.status_code == 422
    assert bad_type.json()["error"]["code"] == "VALIDATION_ERROR"

    empty = client.post(
        "/api/evidence",
        headers=headers,
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert empty.status_code == 422
    assert "empty" in empty.json()["error"]["message"].lower()


def test_public_file_verify_unknown_hash(client):
    """Feature 1: /api/verify/file needs no login; an unknown hash is Unknown."""
    digest = hashlib.sha256(b"a file nobody ever anchored").hexdigest()
    resp = client.post(
        "/api/verify/file",
        files={"file": ("mystery.pdf", b"a file nobody ever anchored", "application/pdf")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["state"] == "Unknown"
    assert body["presented_hash"] == digest
    assert body["onchain_hash"] is None
