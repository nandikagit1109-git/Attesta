# Contributing to TrustPass

Thanks for helping build TrustPass for DecentraHack 2.0 (and beyond).

## Ground rules (non-negotiable)

1. **Trust vocabulary is frozen.** Exactly three states everywhere — UI, API, docs:
   `AI-extracted (unverified)` · `Issuer-verified` · `Revoked or tampered`.
   Never invent a fourth label; never soften "unverified".
2. **AI output is a suggestion, never proof.** The Evidence Verification Agent never claims a document is authentic; only issuer-signed, hash-matching, non-revoked records are "verified".
3. **On-chain = hashes only.** No PDFs, images, passwords, Aadhaar/ID numbers, phone numbers, emails or names on the chain. Ever.
4. **No secrets in the repo.** Real keys stay in `.env` (gitignored). `.env.example` holds placeholders only.
5. **Offline-first demo path.** P0 features must work with no internet and no LLM API key (deterministic fallback).

## Getting started

```bash
# backend
cd backend && python -m venv .venv && .venv\Scripts\activate
pip install -e .[dev] && uvicorn app.main:app --reload

# frontend
cd frontend && npm install && npm run dev

# tests
cd backend && pytest
```

## Workflow

- Branch per feature (`feat/...`, `fix/...`, `docs/...`).
- Keep PRs small; every PR touching trust states, credentials, or the contract needs a review note on the trust model.
- Backend changes: add/adjust Pydantic schemas and tests; OpenAPI docs must stay valid.
- Contract changes: Hardhat tests must cover issue, verify, revoke, unauthorized revoke, duplicate ID, tampered hash.

## Commit style

Conventional-ish, present tense, imperative: `feat: skill graph page`, `fix: revoke guard in registry`.
