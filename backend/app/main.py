"""TrustPass API — FastAPI entrypoint.

Stage 1: app factory, CORS, uniform errors, /api/health. Later stages mount
auth, evidence, skills, career, credentials, profiles and audit-log routers.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .errors import register_error_handlers
from .routers import health
from .states import TrustState

logger = logging.getLogger("trustpass")
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
            headers = {k: v for k, v in scope.get("headers") or []}
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
    app = FastAPI(
        title=f"{settings.app_name} API",
        version="0.1.0",
        description=(
            "AI-Powered Verifiable Skill & Achievement Passport.\n\n"
            "Trust states used across every response: "
            f"{TrustState.AI_EXTRACTED.value} · {TrustState.ISSUER_VERIFIED.value} · "
            f"{TrustState.REVOKED_OR_TAMPERED.value}."
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
    return app


app = create_app()
