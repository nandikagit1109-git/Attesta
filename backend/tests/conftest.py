"""Shared pytest fixtures.

Test env vars are set BEFORE any app import, so settings, the SQLAlchemy
engine and the upload storage all point at a throwaway temp dir. The LLM
vars are cleared so every test runs the deterministic fallback (Phase 3
gate: agents must pass with no API key).
"""

import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="attesta-tests-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_TMP, "test.db").replace("\\", "/")
os.environ["UPLOADS_DIR"] = os.path.join(_TMP, "uploads")
os.environ["LLM_BASE_URL"] = ""
os.environ["LLM_MODEL"] = ""
os.environ["LLM_API_KEY"] = ""
os.environ["CORS_ORIGINS"] = "http://test.local"

import pytest  # noqa: E402  (imported after env setup on purpose)
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture()
def client():
    from app.db import Base, engine
    from app.main import create_app

    # Fresh tables per test: API tests must not see each other's rows.
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestClient(create_app())


def demo_login(client: TestClient, role: str) -> tuple[dict, dict]:
    """One-click demo login; returns (auth_headers, user_dict)."""
    resp = client.post(f"/api/auth/demo/{role}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    return {"Authorization": f"Bearer {data['token']}"}, data["user"]


def register(client: TestClient, email: str, role: str = "student", org: str = "") -> tuple[dict, dict]:
    resp = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "password-123",
            "full_name": email.split("@")[0].title(),
            "role": role,
            "org_name": org,
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    return {"Authorization": f"Bearer {data['token']}"}, data["user"]


class _FakeStudent:
    """write_sample_certificate_pdf only needs .full_name."""

    def __init__(self, full_name: str = "Ananya Sharma"):
        self.full_name = full_name


def pdf_bytes(title: str = "Python Programming", issuer: str = "Springfield College") -> bytes:
    """A real generated certificate PDF (the same builder the seed uses)."""
    from app.services.sample_docs import write_sample_certificate_pdf

    path, _sha = write_sample_certificate_pdf(
        _FakeStudent(), title, issuer, out_dir=tempfile.mkdtemp(prefix="attesta-pdf-")
    )
    with open(path, "rb") as fh:
        return fh.read()
