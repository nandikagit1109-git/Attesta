"""Vercel serverless entrypoint for the TrustPass FastAPI app.

Vercel's Python runtime imports `app` from this file. Local dev and Render use
uvicorn instead (see render.yaml / backend README).
"""

import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.main import app  # noqa: E402  (ASGI app consumed by Vercel's Python runtime)
