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
`POST /api/evidence` (multipart file + type/size validation) → orchestrator runs Evidence Verification then Skill Graph → every agent run appended to the audit log and returned in the response. Result is `AI-extracted (unverified)`.

**Issue (issuer)**
Issuer reviews the approval queue (`GET /api/credentials/queue`) → `POST /api/credentials/issue` → backend anchors the SHA-256 via `issueCredential()` signed with the demo key from `.env` (MetaMask optional) → the Integrity Agent immediately re-checks and the evidence becomes `Issuer-verified`. Bulk variant: `POST /api/credentials/bulk` (CSV).

**Verify (anyone, no login)**
The browser computes SHA-256 with Web Crypto → `POST /api/verify/hash` (optionally with `credential_id`, as receipt links do) → hash lookup, on-chain status, revocation → `Issuer-verified` / `Tampered` / `Revoked` / `Unknown` with issuer, block number and transaction hash. The receipt page additionally reads the issuance transaction directly from the node with ethers.js.

**Gap analysis (student)**
`GET /api/career/gap?role=data-analyst` → Career Mentor weights `Issuer-verified` skills above unverified → score, matched, missing skills with priorities, three project ideas, reasoning. Recruiter variant: `POST /api/career/job-match` scores a pasted JD from verified skills only.

**Demo reset**
`POST /api/demo/reset` wipes and rebuilds the canonical dataset (dev only; production refuses). Same code path as `./make seed`.

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
