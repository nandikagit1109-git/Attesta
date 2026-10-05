# Architecture

## Component view

```
┌───────────────────────────── Browser (React + Vite) ─────────────────────────────┐
│  Student: upload, skill graph, gap analysis, share  ·  Issuer: issue/revoke      │
│  Admin: reset + one-click tamper  ·  Recruiter: guest via /s/<token> share link  │
└───────────────┬──────────────────────────────────────────────────────┬───────────┘
                │ REST (JWT)                                           │ Ethers.js v6 (issuer MetaMask, optional)
┌───────────────▼──────────────── FastAPI backend ─────────────────────▼───────────┐
│  Auth (bcrypt + JWT, RBAC)  ·  Evidence  ·  Projects  ·  Skills  ·  Career       │
│  Credentials  ·  Share links (guest recruiters)  ·  Public audit  ·  /api/health │
│                                                                                  │
│  Agent Orchestrator ── 5 agents (Pydantic in/out, confidence, flags, audit run)  │
│  ├ Document Parser (pdfplumber→Tesseract extraction + LLM, fallback:             │
│  │  keyword+taxonomy heuristics)  — never claims authenticity                    │
│  ├ Skill Classifier + Skill Extractor (→ data/skills.json nodes/edges)           │
│  ├ Confidence Scorer (per-extraction confidence)                                 │
│  ├ Profile Summarizer (fact-only summary generation)                             │
│  └ Integrity module (deterministic, NO LLM: sha256, on-chain hash, revocation)   │
│                                                                                  │
│  LLM wrapper: provider-agnostic, strict JSON → Pydantic, 1 retry, fallback       │
│  Storage adapter: local disk now · IPFS/Supabase stubbed (P2)                    │
└───────────────┬───────────────────────────────────────────────────────────────────┘
                │ web3.py (backend adapter)
┌───────────────▼──────────── Hardhat local node (Sepolia-ready, P2) ──────────────┐
│  VerifiableCredentialRegistry.sol                                                │
│  issueCredential() · verifyCredential() · revokeCredential() · getCredential()   │
│  getCredentialByHash() — reverse index docHash → credentialId                    │
│  stores: credentialId, docHash, issuer, recipient, timestamp, revoked            │
│  rules: issuer-only revoke · duplicate IDs and duplicate hashes rejected         │
└───────────────────────────────────────────────────────────────────────────────────┘
```

## Core flows

**Upload → analyze (student)**
`POST /api/evidence` (multipart file + type/size validation) → orchestrator runs the five agents → every agent run is appended to the audit log and returned in the response. Result is `Unverified`.

**Approve skills (student, the consent gate)**
`POST /api/evidence/{id}/approve-skills` records that the student approved the extracted skills. Until then the evidence stays out of the issuer queue and cannot be anchored (409).

**Issue (issuer)**
Issuer reviews the approval queue (`GET /api/credentials/queue`: approved evidence only) → `POST /api/credentials/issue` → backend anchors the SHA-256 via `issueCredential()` signed with the demo key from `.env` (MetaMask optional) → the Integrity module immediately re-checks and the evidence becomes `Verified`. Bulk variant: `POST /api/credentials/bulk` (CSV), same approval gate.

**Verify (anyone, no login)**
The browser computes SHA-256 with Web Crypto → `POST /api/verify/hash` (optionally with `credential_id`, as receipt links and the landing page's optional field do) → a bare hash resolves through the contract's reverse index (`lookup_by_hash`), with the DB mirror as a chain-outage fallback → `Verified` / `Tampered` / `Revoked` / `Not found` with issuer, block number and transaction hash. The receipt page additionally reads the issuance transaction directly from the node with ethers.js.

**Gap analysis (student)**
`GET /api/career/gap?role=data-analyst` → career scoring weights `Verified` skills above unverified → score, matched, missing skills with priorities, three project ideas, reasoning.

**Share (student → guest recruiter)**
`POST /api/profile/share-link` mints one long random token per student (audited) → guest opens `GET /api/share/{token}`: profile, skills with confidence, credentials with on-chain proof, agent trace, no downloads, no enumeration → `POST /api/share/{token}/job-match` scores a pasted JD from verified skills only. Unknown tokens 404.

**Demo reset + tamper (admin)**
`POST /api/demo/reset` wipes and rebuilds the canonical dataset (dev only; production refuses). `POST /api/demo/tamper/{credential_id}` (admin, dev only) flips one byte in a stored copy, marks the credential page HASH MISMATCH and writes an off-chain tamper entry. Same seed code path as `./make seed`.

## Key principles

1. **Single source of truth for trust states** — `backend/app/states.py`, mirrored in `frontend/src/lib/trustStates.ts`. The Integrity module is the only component allowed to emit verified/revoked/tampered states.
2. **LLM-optional** — strict-JSON Pydantic-validated LLM calls with one retry; a deterministic keyword+taxonomy fallback reproduces the full pipeline with zero API keys (demo safety).
3. **Fail loud on trust, never soft** — if the chain is unreachable, verification returns an explicit error, never a silent "probably fine".
4. **Audit everything** — every agent run is logged; tamper demo and revocation are auditable end-to-end.
5. **Laptop-friendly** — SQLite by default, local Hardhat node, pdfplumber first; PostgreSQL/IPFS/Sepolia are env-var switches (P2).

## API surface (P0)

| Method & path | Purpose |
|---|---|
| `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/demo/{role}` | JWT auth, student/issuer/admin |
| `POST /api/evidence`, `GET /api/evidence/{id}`, `POST /api/evidence/{id}/approve-skills` | Upload + agent analysis + the student consent gate |
| `POST /api/projects`, `GET /api/skills`, `GET /api/career/gap` | Projects, skill graph, gap analysis |
| `POST /api/credentials/issue`, `POST /api/credentials/{id}/revoke`, `POST /api/verify/hash` | Issuer lifecycle + public verification |
| `POST /api/profile/share-link`, `GET /api/share/{token}`, `POST /api/share/{token}/job-match` | One guest token per student; no directory |
| `GET /api/audit` | Public chain-event + off-chain tamper trail (no PII) |
| `POST /api/demo/reset`, `POST /api/demo/tamper/{credential_id}` | Admin demo controls (dev only) |
| `GET /api/health` | Liveness + declared trust states |

Every endpoint: Pydantic request/response schemas + standard error format (`{ "error": { "code", "message", "details" } }`). OpenAPI docs at `/docs`.
