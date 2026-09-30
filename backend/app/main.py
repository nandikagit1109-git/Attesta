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
    register_error_handlers(app)
    app.include_router(health.router)
    return app


app = create_app()
