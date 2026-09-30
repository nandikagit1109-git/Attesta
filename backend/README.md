# Backend

FastAPI service for TrustPass. See the [root README](../README.md) and [architecture](../docs/architecture.md).

## Run (dev)

```bash
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -e .[dev,extraction,chain]
uvicorn app.main:app --reload                    # http://localhost:8000
```

## Layout

```
app/
├── main.py            app factory, CORS, error handlers
├── config.py          pydantic-settings (backend/.env)
├── states.py          canonical trust states + error codes (single source of truth)
├── errors.py          standard {"error": {...}} envelope
├── routers/           endpoint modules (Stage 2+)
├── agents/            orchestrator + 5 agents (Stage 3)
├── storage/           document storage adapter (Stage 2/3)
└── models/            SQLAlchemy models (Stage 2)
tests/                 pytest (health contract tests in Stage 1)
```

## Rules

- Every endpoint: Pydantic request/response schemas + the standard error envelope.
- Trust states: use `app/states.py` only. The Integrity Agent alone decides verified/revoked.
- No secrets in code; load from `.env` (template at `../.env.example`).
