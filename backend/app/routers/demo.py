"""Demo utilities: one-click reset of the sample dataset.

Backs the "Reset demo data" button (feature 5). Deliberately destructive
and dev-only: in production this endpoint refuses to run so a hosted
deployment can never have its data wiped by a stray click.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..services.demo_seed import reset_demo_data

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.post("/reset")
def reset(db: Session = Depends(get_db)):
    if get_settings().environment == "production":
        raise HTTPException(status_code=403, detail="Demo reset is disabled in production")
    return reset_demo_data(db)
