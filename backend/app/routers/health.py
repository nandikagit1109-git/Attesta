"""Health and service-status endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from ..config import get_settings
from ..states import TrustState

router = APIRouter(prefix="/api", tags=["health"])


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    time: str
    trust_states: list[str]
    llm_mode: str


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version="0.1.0",
        time=datetime.now(timezone.utc).isoformat(),
        trust_states=[s.value for s in TrustState],
        llm_mode="llm" if settings.llm_configured else "deterministic-fallback",
    )
