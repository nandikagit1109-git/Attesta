# Contributing to Attesta

Thanks for helping build Attesta for DecentraHack 2.0 (and beyond).

## Ground rules (non-negotiable)

1. **Trust vocabulary is frozen.** Exactly five states everywhere — UI, API, docs:
   `AI-extracted (unverified)` · `Issuer-verified` · `Revoked` · `Tampered` · and
   `Unknown` (public verify page only, when a hash is not anchored).
   Canonical source: `backend/app/states.py`.
2. **AI output is a suggestion, never proof.** The Evidence Verification Agent never claims a document is authentic; only an on-chain record plus a matching hash plus no revocation is "Issuer-verified".
3. **Only the Integrity Agent sets proof states.** Deterministic code, no LLM. No other component may move evidence to verified / revoked / tampered.
4. **On-chain = hashes only.** No PDFs, images, passwords, ID numbers, phone numbers, emails or names on the chain. Ever.
5. **No secrets in the repo.** Real keys stay in `.env` (gitignored). `.env.example` holds placeholders only.
6. **Offline-first demo path.** Everything must work with no internet and no LLM API key (deterministic fallback). The demo path is verified by `./make check` before every phase ends.

## Getting started

```bash
./make install        # backend venv (3.11) + frontend + blockchain deps
./make chain          # local Hardhat node + deploy the registry
./make check          # full gate: tests, build, seed, demo check
```

Individual gates: `./make test-contracts`, `./make test-backend`, `./make test-agents`, `./make build`, `./make lint`.

On Windows use Git Bash (`./make ...`); on Linux/macOS plain `make` works — both delegate to `scripts/make.py`.

## Workflow

- Branch per feature (`feat/...`, `fix/...`, `docs/...`).
- Keep PRs small; any PR touching trust states, credentials, or the contract needs a note on how the trust model is affected.
- Backend changes: add/adjust Pydantic schemas and tests; the standard error envelope `{"error": {"code", "message", "details"}}` must stay uniform.
- Contract changes: Hardhat tests must cover issue, verify, revoke, unauthorized revoke, duplicate ID and tampered hash.
- Frontend: strict TypeScript; trust cues are border style + label, never color alone.

## Commit style

Conventional-ish, present tense, imperative: `feat: receipt file checker`, `fix: revoke guard in registry`.
