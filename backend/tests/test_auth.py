"""Auth: register, login, me, demo logins, role guards, error envelopes."""

from tests.conftest import demo_login, register


def test_register_login_me_roundtrip(client):
    headers, user = register(client, "roundtrip@test.dev", "student")
    assert user["role"] == "student"
    assert user["public_fields"]["email"] is False  # privacy default

    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "roundtrip@test.dev"

    login = client.post(
        "/api/auth/login",
        json={"email": "ROUNDTRIP@test.dev", "password": "password-123"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["id"] == user["id"]


def test_register_rejects_short_password_and_bad_role(client):
    short = client.post(
        "/api/auth/register",
        json={"email": "short@test.dev", "password": "short", "full_name": "S", "role": "student"},
    )
    assert short.status_code == 422
    assert short.json()["error"]["code"] == "VALIDATION_ERROR"

    bad_role = client.post(
        "/api/auth/register",
        json={"email": "admin@test.dev", "password": "password-123", "full_name": "A", "role": "admin"},
    )
    assert bad_role.status_code == 422


def test_register_rejects_duplicate_email(client):
    register(client, "dupe@test.dev", "issuer")
    dupe = client.post(
        "/api/auth/register",
        json={"email": "dupe@test.dev", "password": "password-123", "full_name": "D", "role": "student"},
    )
    assert dupe.status_code == 409
    assert dupe.json()["error"]["code"] == "CONFLICT"


def test_login_wrong_password_is_401_envelope(client):
    register(client, "wrongpw@test.dev")
    resp = client.post(
        "/api/auth/login",
        json={"email": "wrongpw@test.dev", "password": "not-the-password"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "AUTHENTICATION_ERROR"


def test_demo_login_all_roles_creates_users_on_fresh_db(client):
    for role, expected_email in (
        ("student", "student@attesta.demo"),
        ("issuer", "issuer@attesta.demo"),
        ("recruiter", "recruiter@attesta.demo"),
    ):
        _headers, user = demo_login(client, role)
        assert user["email"] == expected_email
        assert user["role"] == role
    # Idempotent: second login returns the same account.
    _, again = demo_login(client, "student")
    assert again["email"] == "student@attesta.demo"


def test_demo_login_unknown_role_404(client):
    assert client.post("/api/auth/demo/admin").status_code == 404


def test_missing_token_is_401(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "AUTHENTICATION_ERROR"


def test_garbage_token_is_401(client):
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert resp.status_code == 401


def test_role_guards_block_wrong_roles(client):
    student_headers, _ = demo_login(client, "student")
    issuer_queue = client.get("/api/credentials/queue", headers=student_headers)
    assert issuer_queue.status_code == 403
    assert issuer_queue.json()["error"]["code"] == "PERMISSION_DENIED"

    recruiter_headers, _ = demo_login(client, "recruiter")
    graph = client.get("/api/skills/graph", headers=recruiter_headers)
    assert graph.status_code == 403


def test_students_get_backend_generated_wallet(client):
    _, user = register(client, "wallet@test.dev", "student")
    assert user["wallet_address"].startswith("0x") and len(user["wallet_address"]) == 42
