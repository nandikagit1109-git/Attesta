"""Health endpoint contract tests (Stage 1 gate)."""

import importlib

from fastapi.testclient import TestClient


def _client() -> TestClient:
    from app.main import create_app

    return TestClient(create_app())


def test_health_ok() -> None:
    resp = _client().get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "TrustPass"


def test_health_declares_exactly_three_trust_states() -> None:
    resp = _client().get("/api/health")
    states = resp.json()["trust_states"]
    assert states == [
        "AI-extracted (unverified)",
        "Issuer-verified",
        "Revoked or tampered",
    ]


def test_error_format_is_standard_envelope() -> None:
    resp = _client().get("/api/definitely-not-a-route")
    assert resp.status_code == 404
    err = resp.json()["error"]
    assert set(err.keys()) == {"code", "message", "details"}
    assert err["code"] == "NOT_FOUND"


def test_settings_defaults_work_offline() -> None:
    settings = importlib.import_module("app.config").get_settings()
    assert settings.llm_configured is False  # demo must run with no API key
    assert ".pdf" in settings.allowed_extension_list
