"""Tests for the public doors the frontend depends on: the guest share link
(one token, one profile, no login, no enumeration) and chain coordinates
(direct on-chain reads from the browser)."""

from tests.conftest import demo_login


def test_share_link_works_for_guests_and_cannot_enumerate(client):
    student_headers, student = demo_login(client, "student")

    # The student publishes the link.
    resp = client.post("/api/profile/share-link", headers=student_headers)
    assert resp.status_code == 200, resp.text
    token = resp.json()["share_token"]
    assert len(token) >= 32  # long random token, not a user id
    assert resp.json()["share_path"] == f"/s/{token}"

    # Idempotent: publishing again returns the same token.
    again = client.post("/api/profile/share-link", headers=student_headers)
    assert again.json()["share_token"] == token

    # A guest (no Authorization header at all) opens the shared profile.
    shared = client.get(f"/api/share/{token}")
    assert shared.status_code == 200, shared.text
    body = shared.json()
    assert body["student"]["full_name"] == "Ananya Sharma"
    assert body["share_token"] == token
    assert isinstance(body["credentials"], list)
    assert isinstance(body["skills"], list)

    # Issuers have no share link: the token is a student feature.
    issuer_headers, _ = demo_login(client, "issuer")
    assert client.post("/api/profile/share-link", headers=issuer_headers).status_code == 403

    # There is no directory, no search, no listing: enumeration is impossible.
    assert client.get("/api/profiles").status_code == 404
    assert client.get(f"/api/profiles/{student['id']}").status_code == 404

    # An unknown token is a plain 404 with no hints.
    assert client.get("/api/share/not-a-real-token").status_code == 404


def test_chain_info_reports_public_coordinates(client):
    resp = client.get("/api/chain")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["chain_id"] == 31337
    assert body["rpc_url"].startswith("http")
    # deployed is False on a fresh test DB with no chain.json contract address
    assert isinstance(body["deployed"], bool)
    assert body["contract_address"] == "" or body["contract_address"].startswith("0x")
