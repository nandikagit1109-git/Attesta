"""Credentials + public verify flow with the chain mocked.

The fake chain behaves like the real registry (issue, verify, revoke) but
lives in memory, so these tests run offline while exercising the exact
status transitions the demo depends on.
"""

import pytest

from tests.conftest import FakeChain, demo_login, pdf_bytes, register


@pytest.fixture()
def fake_chain(monkeypatch):
    from app import chain as chain_module

    fake = FakeChain()
    monkeypatch.setattr(chain_module, "issue_onchain", fake.issue_onchain)
    monkeypatch.setattr(chain_module, "verify_onchain", fake.verify_onchain)
    monkeypatch.setattr(chain_module, "get_onchain_credential", fake.get_onchain_credential)
    monkeypatch.setattr(chain_module, "revoke_onchain", fake.revoke_onchain)
    return fake


def _student_upload(client):
    student_headers, student = demo_login(client, "student")
    resp = client.post(
        "/api/evidence",
        headers=student_headers,
        files={"file": ("python-cert.pdf", pdf_bytes(), "application/pdf")},
        data={"title": "Python Programming"},
    )
    assert resp.status_code == 200, resp.text
    return student_headers, student, resp.json()


def test_issue_flow_moves_evidence_to_issuer_verified(client, fake_chain):
    _student_headers, _student, evidence = _student_upload(client)
    issuer_headers, _issuer = demo_login(client, "issuer")

    queue = client.get("/api/credentials/queue", headers=issuer_headers)
    assert queue.status_code == 200
    assert any(e["id"] == evidence["id"] for e in queue.json()["pending"])

    issued = client.post("/api/credentials/issue", headers=issuer_headers, json={"evidence_id": evidence["id"]})
    assert issued.status_code == 200, issued.text
    cred = issued.json()["credential"]
    assert cred["tx_hash"].startswith("0x") and cred["block_number"] >= 1
    assert cred["recipient_address"]  # student wallet generated at registration

    body = issued.json()["evidence"]
    assert body["trust_state"] == "Issuer-verified"
    # Extracted skills become verified with the credential.
    assert all(s["verified"] for s in body["skills"] if s["id"])

    # Queue moves the evidence out of pending.
    queue_after = client.get("/api/credentials/queue", headers=issuer_headers).json()
    assert not any(e["id"] == evidence["id"] for e in queue_after["pending"])


def test_issue_requires_issuer_and_blocks_duplicates(client, fake_chain):
    _student_headers, _student, evidence = _student_upload(client)
    student_headers, _ = demo_login(client, "student")
    recruiter_headers, _ = demo_login(client, "recruiter")

    student_issue = client.post(
        "/api/credentials/issue", headers=student_headers, json={"evidence_id": evidence["id"]}
    )
    recruiter_issue = client.post(
        "/api/credentials/issue", headers=recruiter_headers, json={"evidence_id": evidence["id"]}
    )
    assert student_issue.status_code == 403
    assert recruiter_issue.status_code == 403

    issuer_headers, _ = demo_login(client, "issuer")
    issued = client.post("/api/credentials/issue", headers=issuer_headers, json={"evidence_id": evidence["id"]})
    assert issued.status_code == 200
    dup = client.post("/api/credentials/issue", headers=issuer_headers, json={"evidence_id": evidence["id"]})
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "CONFLICT"


def test_public_verify_hash_shows_on_chain_proof(client, fake_chain):
    _student_headers, _student, evidence = _student_upload(client)
    issuer_headers, _ = demo_login(client, "issuer")
    cred = client.post(
        "/api/credentials/issue", headers=issuer_headers, json={"evidence_id": evidence["id"]}
    ).json()["credential"]

    # Feature 1: anonymous verification, no login, full provenance.
    resp = client.post("/api/verify/hash", json={"sha256": evidence["sha256"]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["state"] == "Issuer-verified"
    assert body["hash_match"] is True
    assert body["issuer_address"] == fake_chain.ISSUER
    assert body["tx_hash"] == cred["tx_hash"]
    assert body["block_number"] == cred["block_number"]
    assert body["onchain_hash"] == "0x" + evidence["sha256"]


def test_verify_by_credential_id_returns_404_for_unknown_id(client, fake_chain):
    resp = client.post(
        "/api/verify/hash", json={"sha256": "0" * 64, "credential_id": "nope"}
    )
    assert resp.status_code == 404


def test_tampered_file_fails_against_the_credential(client, fake_chain):
    student_headers, _student, evidence = _student_upload(client)
    issuer_headers, _ = demo_login(client, "issuer")
    cred = client.post(
        "/api/credentials/issue", headers=issuer_headers, json={"evidence_id": evidence["id"]}
    ).json()["credential"]

    tamper = client.post(f"/api/evidence/{evidence['id']}/tamper", headers=student_headers)
    tampered_hash = tamper.json()["tampered_sha256"]

    # Verifying the tampered bytes against the anchored credential fails honestly.
    resp = client.post(
        "/api/verify/hash",
        json={"sha256": tampered_hash, "credential_id": cred["id"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["state"] == "Tampered"
    assert body["hash_match"] is False
    assert body["onchain_hash"] == "0x" + evidence["sha256"]
    assert body["presented_hash"] == tampered_hash


def test_revoke_flow_with_reason_visible_on_public_verify(client, fake_chain):
    student_headers, _student, evidence = _student_upload(client)
    issuer_headers, _issuer = demo_login(client, "issuer")
    cred = client.post(
        "/api/credentials/issue", headers=issuer_headers, json={"evidence_id": evidence["id"]}
    ).json()["credential"]

    # A different issuer cannot revoke someone else's credential.
    other_issuer_headers, _ = register(client, "other-issuer@test.dev", role="issuer", org="Other College")
    forbidden = client.post(
        f"/api/credentials/{cred['id']}/revoke",
        headers=other_issuer_headers,
        json={"reason": "not mine"},
    )
    assert forbidden.status_code == 403

    no_reason = client.post(
        f"/api/credentials/{cred['id']}/revoke", headers=issuer_headers, json={"reason": ""}
    )
    assert no_reason.status_code == 422

    revoke = client.post(
        f"/api/credentials/{cred['id']}/revoke",
        headers=issuer_headers,
        json={"reason": "Certificate issued in error"},
    )
    assert revoke.status_code == 200
    assert revoke.json()["revoked"] is True
    assert revoke.json()["revoke_reason"] == "Certificate issued in error"

    # Evidence flips to Revoked; the original hash now verifies as Revoked.
    detail = client.get(f"/api/evidence/{evidence['id']}", headers=student_headers).json()
    assert detail["trust_state"] == "Revoked"

    again = client.post(
        "/api/verify/hash", json={"sha256": evidence["sha256"], "credential_id": cred["id"]}
    )
    assert again.json()["state"] == "Revoked"
    assert again.json()["revoke_reason"] == "Certificate issued in error"
    assert again.json()["revoked"] is True

    double = client.post(
        f"/api/credentials/{cred['id']}/revoke", headers=issuer_headers, json={"reason": "again"}
    )
    assert double.status_code == 409


def test_csv_bulk_issuance_creates_students_and_credentials(client, fake_chain):
    issuer_headers, issuer = demo_login(client, "issuer")
    _student_headers, student = demo_login(client, "student")

    csv_content = (
        "student_email,title,file_name\n"
        f"{student['email']},SQL Fundamentals,sql-cert.pdf\n"
        "new.bulk.student@test.dev,Excel for Analysts,excel-cert.pdf\n"
        "broken-row@test.dev,,missing-title.csv\n"
    )
    resp = client.post(
        "/api/credentials/bulk",
        headers=issuer_headers,
        files={"file": ("batch.csv", csv_content.encode("utf-8"), "text/csv")},
    )
    assert resp.status_code == 200, resp.text
    results = resp.json()["results"]
    assert [r["status"] for r in results] == ["issued", "issued", "error"]
    assert results[0]["tx_hash"].startswith("0x")

    # The new student exists with a wallet, evidence and an on-chain credential.
    from app.db import SessionLocal
    from app.models import Credential, Evidence, User

    db = SessionLocal()
    try:
        new_student = db.query(User).filter(User.email == "new.bulk.student@test.dev").first()
        assert new_student is not None and new_student.wallet_address.startswith("0x")
        evidences = db.query(Evidence).filter(Evidence.student_id == new_student.id).all()
        assert len(evidences) == 1 and evidences[0].trust_state == "Issuer-verified"
        assert db.query(Credential).filter(Credential.issuer_id == issuer["id"]).count() == 2
    finally:
        db.close()

    bad = client.post(
        "/api/credentials/bulk",
        headers=issuer_headers,
        files={"file": ("bad.csv", b"a,b\n1,2", "text/csv")},
    )
    assert bad.status_code == 422
    not_csv = client.post(
        "/api/credentials/bulk",
        headers=issuer_headers,
        files={"file": ("batch.txt", csv_content.encode("utf-8"), "text/plain")},
    )
    assert not_csv.status_code == 422


def test_audit_log_records_issue_revoke_verify(client, fake_chain):
    student_headers, _student, evidence = _student_upload(client)
    issuer_headers, _ = demo_login(client, "issuer")
    cred = client.post(
        "/api/credentials/issue", headers=issuer_headers, json={"evidence_id": evidence["id"]}
    ).json()["credential"]
    client.post("/api/verify/hash", json={"sha256": evidence["sha256"]})
    client.post(
        f"/api/credentials/{cred['id']}/revoke", headers=issuer_headers, json={"reason": "demo"}
    )

    issuer_audit = client.get("/api/audit", headers=issuer_headers).json()
    actions = {row["action"] for row in issuer_audit}
    assert {"ISSUE", "REVOKE", "VERIFY", "AGENT_RUN", "UPLOAD"} <= actions
    assert any(row["actor_role"] == "anonymous" for row in issuer_audit)  # public verify is audited

    # Students see only their own trail (feature 10 privacy).
    student_audit = client.get("/api/audit", headers=student_headers).json()
    assert student_audit
    assert all(row["actor_id"] for row in student_audit)
