"""Tests for the public endpoints the frontend depends on: the student
directory (recruiter search source, privacy-honoring) and chain coordinates
(direct on-chain reads from the browser)."""

from tests.conftest import demo_login


def test_student_directory_honors_privacy_toggles(client):
    _, student = demo_login(client, "student")
    resp = client.get("/api/profiles")
    assert resp.status_code == 200, resp.text
    entries = resp.json()
    assert len(entries) == 1
    entry = entries[0]
    assert entry["user_id"] == student["id"]
    assert entry["full_name"] == "Ananya Sharma"
    # Default toggles: headline public, email private.
    assert entry["headline"]
    assert "email" not in entry
    # Skills included by default (empty until evidence exists).
    assert entry["skills"] == {"verified": [], "unverified": []}

    # The student can hide everything with one PATCH.
    hidden = client.patch(
        "/api/profile/me",
        headers={"Authorization": f"Bearer {_token(client, 'student')}"},
        json={"public_fields": {"full_name": False, "headline": False, "skills": False}},
    )
    assert hidden.status_code == 200, hidden.text
    after = client.get("/api/profiles").json()[0]
    assert set(after.keys()) == {"user_id", "wallet_address"}


def test_chain_info_reports_public_coordinates(client):
    resp = client.get("/api/chain")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["chain_id"] == 31337
    assert body["rpc_url"].startswith("http")
    # deployed is False on a fresh test DB with no chain.json contract address
    assert isinstance(body["deployed"], bool)
    assert body["contract_address"] == "" or body["contract_address"].startswith("0x")


def _token(client, role) -> str:
    return demo_login(client, role)[0]["Authorization"].split(" ", 1)[1]
