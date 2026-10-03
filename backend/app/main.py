"""Attesta API — FastAPI entrypoint.

App factory: CORS, uniform error envelope, database init, and every router
(auth, evidence, credentials, public verify, skills/projects, career,
profiles, audit log). This module is also the Vercel serverless entrypoint
(see api/index.py).
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import init_db
from .errors import register_error_handlers
from .routers import (
    audit,
    auth,
    career,
    credentials,
    evidence,
    health,
    profiles,
    skills,
    verify,
)
from .states import TrustState

logger = logging.getLogger("attesta")
logging.basicConfig(level=logging.INFO)


class VercelPathRewriteMiddleware:
    """Restore the original request path on Vercel.

    When vercel.json rewrites route e.g. /api/health to the single serverless
    function /api/index.py, the ASGI scope may carry the *destination* path.
    Vercel exposes the original path in the x-vercel-rewrite header; put it
    back so FastAPI routes match. No-op everywhere else.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers") or [])
            original = headers.get(b"x-vercel-rewrite")
            if original:
                from urllib.parse import urlsplit

                path = original.decode("latin-1")
                if "://" in path:  # tolerate full-URL values
                    path = urlsplit(path).path or "/"
                scope["path"] = path
                scope["raw_path"] = path.encode("latin-1")
        await self.app(scope, receive, send)


def create_app() -> FastAPI:
    settings = get_settings()
    init_db()  # tables must exist before the first request (SQLite / serverless)
    app = FastAPI(
        title=f"{settings.app_name} API",
        version="0.1.0",
        description=(
            "Attesta — verified credentials for students. AI agents analyze evidence, "
            "issuers confirm it, SHA-256 hashes are anchored on-chain, and anyone can "
            "verify a file without trusting Attesta's servers.\n\n"
            "Trust states used across every response: "
            f"{TrustState.AI_EXTRACTED.value} · {TrustState.ISSUER_VERIFIED.value} · "
            f"{TrustState.REVOKED.value} · {TrustState.TAMPERED.value} · "
            f"{TrustState.UNKNOWN.value}."
        ),
    )
    origins = settings.cors_origin_list
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=origins != ["*"],  # wildcard + credentials is invalid per CORS spec
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(VercelPathRewriteMiddleware)
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(evidence.router)
    app.include_router(credentials.router)
    app.include_router(verify.router)
    app.include_router(skills.router)
    app.include_router(skills.projects_router)
    app.include_router(career.router)
    app.include_router(profiles.router)
    app.include_router(profiles.public_router)
    app.include_router(audit.router)
    return app


app = create_app()
