# Architecture

## Component view

```
┌───────────────────────────── Browser (React + Vite) ─────────────────────────────┐
│  Student: upload, skill graph, gap analysis, share  ·  Issuer: issue/revoke      │
│  Recruiter: public profile + QR → verify  ·  trust-state badges everywhere       │
└───────────────┬──────────────────────────────────────────────────────┬───────────┘
                │ REST (JWT)                                           │ Ethers.js v6 (issuer MetaMask, optional)
┌───────────────▼──────────────── FastAPI backend ─────────────────────▼───────────┐
│  Auth (bcrypt + JWT, RBAC)  ·  Evidence  ·  Projects  ·  Skills  ·  Career       │
│  Credentials  ·  Public profiles  ·  Audit log  ·  /api/health                   │
│                                                                                  │
│  Agent Orchestrator ── 5 agents (Pydantic in/out, confidence, flags, audit run)  │
│  ├ Evidence Verification (pdfplumber→Tesseract extraction + LLM, fallback:       │
│  │  keyword+taxonomy heuristics)  — never claims authenticity                    │
│  ├ Skill Graph (maps evidence → data/skills.json nodes/edges)                    │
│  ├ Career Mentor (verified > unverified weighting, gap analysis)                  │
│  ├ Integrity (deterministic, NO LLM: sha256, on-chain hash, revocation)          │
│  └ Profile (fact-only summary generation)                                        │
│                                                                                  │
│  LLM wrapper: provider-agnostic, strict JSON → Pydantic, 1 retry, fallback       │
│  Storage adapter: local disk now · IPFS/Supabase stubbed (P2)                    │
└───────────────┬───────────────────────────────────────────────────────────────────┘
                │ web3.py (backend adapter)
┌───────────────▼──────────── Hardhat local node (Sepolia-ready, P2) ──────────────┐
│  VerifiableCredentialRegistry.sol                                                │
│  issueCredential() · verifyCredential() · revokeCredential() · getCredential()   │
│  stores: credentialId, docHash, issuer, recipient, timestamp, revoked            │
│  rules: issuer-only revoke · duplicate IDs rejected · Issue/Revoke events        │
└───────────────────────────────────────────────────────────────────────────────────┘
```

## Core flows

**Upload → analyze (student)**
`POST /api/evidence/upload` (file + type validation) → `POST /api/evidence/analyze` → orchestrator runs Evidence Verification then Skill Graph → every agent run appended to the audit log (agent name, input hash, output, model, fallback-used, timestamp). Result is `AI-extracted (unverified)`.

**Issue (issuer)**
Issuer reviews extracted fields → `POST /api/credentials/issue` → backend anchors SHA-256 hash via `issueCredential()` (MetaMask signature by issuer, or demo key from `.env`) → student's item becomes `Issuer-verified`.

**Verify (recruiter/QR)**
`GET /api/profiles/{username}` renders opted-in profile → Integrity Agent runs per credential: recompute SHA-256 of the referenced document, compare with on-chain hash, check revocation → `match` / `mismatch` / `revoked` with reasons → UI badge.

**Gap analysis (student)**
`POST /api/career/analyze` with target role from `data/roles.json` → Career Mentor weights `Issuer-verified` skills above unverified → missing skills, learning priorities, three project ideas, portfolio improvements.

## Key principles

1. **Single source of truth for trust states** — `backend/app/states.py`, mirrored in `frontend/src/lib/trustStates.ts`. The Integrity Agent is the only component allowed to emit verified/revoked-or-tampered states.
2. **LLM-optional** — strict-JSON Pydantic-validated LLM calls with one retry; a deterministic keyword+taxonomy fallback reproduces the full pipeline with zero API keys (demo safety).
3. **Fail loud on trust, never soft** — if the chain is unreachable, verification returns an explicit error, never a silent "probably fine".
4. **Audit everything** — every agent run is logged; tamper demo and revocation are auditable end-to-end.
5. **Laptop-friendly** — SQLite by default, local Hardhat node, pdfplumber first; PostgreSQL/IPFS/Sepolia are env-var switches (P2).

## API surface (P0)

| Method & path | Purpose |
|---|---|
| `POST /api/auth/register`, `POST /api/auth/login` | JWT auth, three roles |
| `POST /api/evidence/upload`, `GET /api/evidence`, `POST /api/evidence/analyze` | Document upload + agent analysis |
| `POST /api/projects`, `GET /api/skills` | Projects & skill graph |
| `POST /api/career/analyze` | Target-role gap analysis |
| `POST /api/credentials/issue`, `POST /api/credentials/revoke`, `GET /api/credentials/{id}/verify` | Issuer lifecycle + integrity check |
| `GET /api/profiles/{username}` | Opted-in public profile |
| `GET /api/audit-log` | Agent + action audit trail |
| `GET /api/health` | Liveness (this stage) |

Every endpoint: Pydantic request/response schemas + standard error format (`{ "error": { "code", "message", "details" } }`). OpenAPI docs at `/docs`.
