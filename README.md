# TrustPass — AI-Powered Verifiable Skill & Achievement Passport

> Student skill identity: AI agents extract evidence, issuers sign credentials on-chain, recruiters verify without trusting our servers.

**DecentraHack 2.0** — themes: Agentic AI · Blockchain/Web3 · Open Source. Live offline demo: **9 October 2026**.

## Problem

Certificates, projects, internships and hackathon results are scattered across platforms. Recruiters can't verify them, colleges verify documents by hand, and students don't know which skills their target career needs.

## Solution

One skill identity: AI agents analyze evidence into a skill graph, issuers confirm credentials, SHA-256 hashes are anchored on a blockchain, and students share a public profile via link or QR code.

## Trust model (the three states — never blurred)

| State | Meaning |
|---|---|
| `AI-extracted (unverified)` | An AI/OCR suggestion extracted from a document. **Never proves authenticity.** |
| `Issuer-verified` | Issuer-signed on-chain record **AND** matching document hash **AND** not revoked. |
| `Revoked or tampered` | Revoked on-chain, or the document hash no longer matches the anchored hash. |

Every UI label and API response uses **only** these three states. The canonical definition lives in
[backend/app/states.py](backend/app/states.py) and is mirrored in [frontend/src/lib/trustStates.ts](frontend/src/lib/trustStates.ts).

## Why blockchain (and why nothing else)

Multiple independent issuers (colleges, companies, hackathon organizers) write credential records, and any recruiter can check them **without trusting TrustPass servers or a single database owner**. The chain gives tamper-evidence: once anchored, nobody — not even us — can quietly rewrite a credential hash.

The chain is used **only** for tamper-evident credential records. It stores: credential ID, document hash, issuer address, recipient address, timestamp, revoked flag. **No tokens, no trading, no speculation.** PDFs, images, passwords, Aadhaar/ID numbers, phone numbers, emails and names never go on-chain.

## Architecture

```
                    ┌──────────────────────────────────────────────┐
                    │                  TrustPass                   │
                    │                                              │
 React + Vite SPA   │   FastAPI backend          Agents            │      Hardhat / Sepolia
 ┌──────────────┐   │   ┌──────────────┐   ┌───────────────────┐  │   ┌─────────────────────┐
 │ Student UI   │──▶│   │ REST API     │──▶│ Orchestrator      │  │   │ VerifiableCredential│
 │ Issuer UI    │   │   │ JWT + RBAC   │   │ ├ Evidence Verify │  │   │ Registry (Solidity) │
 │ Recruiter/QR │◀──│   │ SQLite/PG    │   │ ├ Skill Graph     │  │   │ issue/verify/revoke │
 │ Skill graph  │   │   │ Audit log    │   │ ├ Career Mentor   │  │   │ get Credential      │
 └──────────────┘   │   └──────┬───────┘   │ ├ Integrity       │──┼──▶│ hash anchor only    │
       ▲            │          │           │ └ Profile         │  │   └─────────────────────┘
       │ QR link    │   ┌──────▼───────┐   └───────────────────┘  │
 ┌──────────────┐   │   │ Documents    │   LLM: OpenAI-compatible │
 │ Public       │   │   │ (local disk, │   wrapper + deterministic│
 │ profile      │   │   │ IPFS/Supabase│   keyword fallback —     │
 └──────────────┘   │   │ adapters)    │   works with no API key  │
                    │   └──────────────┘   └───────────────────┘  │
                    └──────────────────────────────────────────────┘
```

## Stack

| Layer | Tech |
|---|---|
| Frontend | React, Vite, Tailwind, React Router, Recharts, React Flow, QR library, Ethers.js v6 |
| Backend | FastAPI, Pydantic, SQLAlchemy, SQLite (PostgreSQL via `DATABASE_URL`) |
| Extraction | pdfplumber → Tesseract fallback (images/scans) |
| Blockchain | Solidity, Hardhat (local node; Sepolia-ready config) |

## Repository layout

```
trustpass/
├── frontend/     React SPA (student, issuer, recruiter/QR views)
├── backend/      FastAPI app, agents, storage adapter
├── blockchain/   VerifiableCredentialRegistry + Hardhat tests
├── data/         skills.json taxonomy, roles.json (target roles)
├── docs/         architecture, trust model, privacy
├── docker-compose.yml
├── .env.example  copy to backend/.env — never commit real keys
├── LICENSE (MIT) · CONTRIBUTING.md · README.md
```

## Quickstart (Stage 1 skeleton)

```bash
# backend (port 8000)
cd backend
python -m venv .venv && .venv\Scripts\activate     # Windows
pip install -e .[dev]
uvicorn app.main:app --reload

# frontend (port 5173)
cd frontend
npm install
npm run dev
```

- API health: http://localhost:8000/api/health · OpenAPI docs: http://localhost:8000/docs
- Web app: http://localhost:5173
- Local chain (Stage 4): `cd blockchain && npm install && npx hardhat node`

## Build stages

- [x] **Stage 1** — Repo skeleton, trust-state vocabulary, health endpoints, boots locally
- [ ] **Stage 2** — Data models, auth, RBAC, P0 API endpoints
- [ ] **Stage 3** — Agent system (5 agents + orchestrator, LLM wrapper + fallback)
- [ ] **Stage 4** — Smart contract + Hardhat tests + backend chain adapter
- [ ] **Stage 5** — Frontend UX (skill graph, gap analysis, QR, tamper demo)
- [ ] **Stage 6** — Seed data, demo script, offline hardening
- [ ] **Stage 7** — Submission docs (P2 documented-only: IPFS, testnet, bulk issuance)

## Privacy

Public profiles expose only fields the student opted in to. Documents stay off-chain in local storage behind a storage-adapter interface (IPFS/Supabase adapters stubbed). Passwords hashed with bcrypt, JWT auth, file type/size validation, no secrets in the repo.

## License

MIT — see [LICENSE](LICENSE).
