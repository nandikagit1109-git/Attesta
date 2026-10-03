"""Health endpoint contract tests."""

import importlib


def test_health_ok(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["app"] == "Attesta"
    assert body["llm_mode"] == "deterministic-fallback"  # demo must work with no API key


def test_health_declares_the_documented_trust_states(client):
    resp = client.get("/api/health")
    states = resp.json()["trust_states"]
    assert states == [
        "AI-extracted (unverified)",
        "Issuer-verified",
        "Revoked",
        "Tampered",
    ]


def test_error_format_is_standard_envelope(client):
    resp = client.get("/api/definitely-not-a-route")
    assert resp.status_code == 404
    err = resp.json()["error"]
    assert set(err.keys()) == {"code", "message", "details"}
    assert err["code"] == "NOT_FOUND"


def test_settings_defaults_work_offline():
    settings = importlib.import_module("app.config").get_settings()
    assert settings.llm_configured is False  # demo must run with no API key
    assert ".pdf" in settings.allowed_extension_list
    assert settings.max_upload_bytes == settings.max_upload_mb * 1024 * 1024


def test_openapi_documents_the_api(client):
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    paths = resp.json()["paths"]
    for required in (
        "/api/health",
        "/api/auth/demo/{role}",
        "/api/evidence",
        "/api/credentials/issue",
        "/api/verify/hash",
        "/api/verify/file",
        "/api/skills/graph",
        "/api/career/job-match",
        "/api/profiles/{user_id}",
        "/api/audit",
    ):
        assert required in paths, f"missing route {required}"
