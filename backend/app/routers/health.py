"""Health check — used by Vercel, Render and demo_check."""

from fastapi import APIRouter

from ..agents.llm import llm_available
from ..config import get_settings
from ..states import TrustState

router = APIRouter()


@router.get("/api/health")
def health():
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "trust_states": [
            TrustState.AI_EXTRACTED.value,
            TrustState.ISSUER_VERIFIED.value,
            TrustState.REVOKED.value,
            TrustState.TAMPERED.value,
        ],
        "llm_mode": "llm" if llm_available() else "deterministic-fallback",
    }
