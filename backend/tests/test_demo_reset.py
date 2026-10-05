"""The /api/demo/reset endpoint (UI "Reset demo data" button) with the chain
faked: wipes the database and rebuilds the canonical demo dataset."""

from tests.conftest import demo_login


def test_reset_rebuilds_the_full_demo_dataset(client, fake_chain):
    # Reset belongs to the Demo/Admin role now.
    admin_headers, _admin = demo_login(client, "admin")
    resp = client.post("/api/demo/reset", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    seed = resp.json()
    assert len(seed["share_token"]) >= 32  # the guest share link comes seeded

    # Canonical dataset: 3 certificates, 2 on-chain credentials, 1 revoked,
    # 1 pre-staged tampered copy.
    assert seed["verified"]["sha256"] != seed["revoked"]["sha256"]
    assert seed["tampered"]["sha256"] != seed["verified"]["sha256"]
    assert len(seed["verified"]["credential_id"]) == 36
    assert seed["tampered"]["credential_id"] == seed["verified"]["credential_id"]

    headers, user = demo_login(client, "student")
    assert user["email"] == "student@attesta.demo"  # rebuilt with the same identity

    evidence = client.get("/api/evidence", headers=headers).json()
    assert len(evidence) == 3
    states = {e["trust_state"] for e in evidence}
    assert states == {"Verified", "Revoked", "Unverified"}

    # The tampered copy is pre-staged on the verified certificate.
    verified = next(e for e in evidence if e["trust_state"] == "Verified")
    assert verified["has_tampered_copy"] is True

    # Public verify reflects every seeded state.
    r = client.post("/api/verify/hash", json={"sha256": seed["verified"]["sha256"]})
    assert r.json()["state"] == "Verified"
    r = client.post("/api/verify/hash", json={"sha256": seed["revoked"]["sha256"]})
    assert r.json()["state"] == "Revoked"
    r = client.post("/api/verify/hash", json={"sha256": seed["unverified"]["sha256"]})
    assert r.json()["state"] == "Not found"
    r = client.post(
        "/api/verify/hash",
        json={"sha256": seed["tampered"]["sha256"], "credential_id": seed["tampered"]["credential_id"]},
    )
    assert r.json()["state"] == "Tampered"

    # The student's two seeded projects feed the graph and career page.
    projects = client.get("/api/projects", headers=headers).json()
    assert len(projects) == 2


def test_reset_belongs_to_the_admin_role_only(client, fake_chain):
    """Reset is destructive, so it is admin-owned; in production the API also
    refuses regardless of role."""
    assert client.post("/api/demo/reset").status_code == 401  # anonymous
    student_headers, _ = demo_login(client, "student")
    assert client.post("/api/demo/reset", headers=student_headers).status_code == 403
    admin_headers, _ = demo_login(client, "admin")
    assert client.post("/api/demo/reset", headers=admin_headers).status_code == 200
