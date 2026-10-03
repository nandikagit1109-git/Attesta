# Attesta — verified student credentials

> AI agents analyze evidence, issuers confirm, SHA-256 hashes are anchored on-chain, and anyone can verify a file without trusting Attesta's servers.

**DecentraHack 2.0** — themes: Agentic AI · Blockchain/Web3 · Open Source. Live offline demo: 9 October 2026.

## What it does

Students upload certificates, projects and internship letters. Five AI agents read the documents, map skills onto a standard taxonomy, and compare them to a target career. A college issuer approves the evidence and its SHA-256 hash is written to a public blockchain. From then on, anyone — recruiters especially — can verify a file in the browser and get one of four answers, with cryptographic proof:

| State | Meaning |
|---|---|
| `AI-extracted (unverified)` | An agent's suggestion. **Never proof of authenticity.** |
| `Issuer-verified` | On-chain record exists **AND** file hash matches **AND** not revoked. |
| `Revoked` | The original issuer revoked it. Reason and timestamp are public. |
| `Tampered` | The presented hash differs from the anchored hash. Changed hex characters are highlighted. |

`Unknown` appears on the public verify page when a hash is not anchored on-chain at all.

## Why blockchain (and why nothing else)

Several independent issuers (colleges, employers, hackathon organizers) write credential records, and any recruiter can check them **without trusting Attesta's servers or a single database owner**. The chain gives tamper-evidence: once anchored, nobody — not even us — can quietly rewrite a credential hash.

The chain stores **only**: credential ID, document hash, issuer address, recipient address, timestamp, revoked flag. **No tokens, no trading, no speculation.** PDFs, images, passwords, ID numbers, phone numbers, emails and names never go on-chain.

And the proof is re-checkable at the edge: the receipt page reads the issuance transaction **directly from the node with ethers.js in your browser**, so the verdict does not depend on Attesta's API being honest.

## Features

1. Public **Verify any file** page: drop a file, the browser computes SHA-256 (Web Crypto), the app looks it up on-chain and shows Verified / Tampered / Revoked / Unknown with issuer, block number, transaction hash and a side-by-side hash comparison that highlights the changed hex characters.
2. **Agent Trace** panel: every agent run with input summary, output, confidence, flags, duration, and whether the deterministic fallback was used.
3. **Shareable receipt** with permalink and QR code.
4. **Recruiter job match**: paste a job description, get a score computed from issuer-verified skills only, unverified skills listed separately, reasoning shown.
5. **Demo mode**: one-click login as Student / Issuer / Recruiter, a Reset demo data button, and a Tamper with this file button that flips one byte in a stored copy to demonstrate failure.
6. **Skill graph** (React Flow): verified and unverified nodes differ by border style and label, never by color alone. Edges carry extraction strength.
7. **Revocation** with reason and timestamp, visible on the public verify page.
8. **Issuer CSV bulk issuance** (columns: student_email, title, file_name).
9. **Privacy toggles** per profile field; the public profile shows only opted-in fields.
10. **Audit log** of every issue, revoke, verify and agent run.

## Architecture

```mermaid
graph LR
    subgraph Browser
        SPA["React + Vite SPA<br/>student · issuer · recruiter · public"]
        WC["Web Crypto SHA-256<br/>+ ethers.js direct read"]
    end
    subgraph Backend["FastAPI backend"]
        API["REST API · JWT + RBAC<br/>audit log"]
        ORCH["Orchestrator"]
        EV["Evidence<br/>Agent"]
        SG["Skill Graph<br/>Agent"]
        CM["Career Mentor<br/>Agent"]
        IA["Integrity Agent<br/>(no LLM)"]
        PA["Profile<br/>Agent"]
        EX["pdfplumber →<br/>Tesseract fallback"]
    end
    LLM["LLM wrapper<br/>strict JSON + 1 retry<br/>keyword fallback: works offline"]
    CH["VerifiableCredentialRegistry (Solidity)<br/>issue / verify / revoke / getCredential<br/>hash anchor only"]
    DB[("SQLite / PostgreSQL")]

    SPA -->|HTTPS /api| API
    API --> ORCH
    ORCH --> EV & SG & CM & IA & PA
    EV & SG & CM & PA -.->|strict JSON, 1 retry| LLM
    ORCH --> EX
    API --> DB
    IA -->|issue / verify / revoke| CH
    SPA -.->|read tx directly| CH
```

The LLM layer is provider-agnostic (OpenAI-compatible). With no API key everything still works: a deterministic keyword-and-taxonomy fallback produces good results on the seeded certificates, so the demo never depends on the internet.

## Quickstart (3 commands)

```bash
./make install        # backend venv + frontend + blockchain deps
./make chain          # start the local Hardhat node and deploy the registry
./make check          # tests, build, seed the demo data, drive the full demo
```

Then run the app:

```bash
./make demo-check     # already proven by the gate; to serve manually:
cd backend && .venv/Scripts/uvicorn app.main:app --port 8000     # Windows venv path: .venv\Scripts\
cd frontend && npm run dev
```

- Web app: http://localhost:5173
- API health: http://localhost:8000/api/health
- OpenAPI docs: http://localhost:8000/docs

On Linux/macOS use `make` instead of `./make` (same targets; the Makefile delegates to `scripts/make.py`).

## Demo accounts

One click each on the login page — no passwords to type on stage:

| Role | Email | Sees |
|---|---|---|
| Student | `student@attesta.demo` | Uploads, agent trace, skill graph, career gap, receipts |
| Issuer | `issuer@attesta.demo` | Approval queue, on-chain anchoring, CSV bulk, revoke |
| Recruiter | `recruiter@attesta.demo` | Candidate directory, verified-only job match |

Sample data is labeled "Sample data" everywhere it appears. `./make seed` (or the Reset demo data button) rebuilds: 1 student, 1 college issuer, 1 recruiter; 3 real certificate PDFs (Python verified, SQL issued-then-revoked, Excel left unverified); 1 pre-staged tampered copy; 2 projects.

## Screenshots

Placeholders — drop the real captures into `docs/screenshots/` with these names:

| File | Shows |
|---|---|
| `docs/screenshots/landing-verify.png` | Landing page with the live verify box and a verdict |
| `docs/screenshots/verify-diff.png` | Public verify page with the highlighted hash diff on a tampered file |
| `docs/screenshots/agent-trace.png` | Evidence detail with the agent trace panel |
| `docs/screenshots/skill-graph.png` | React Flow skill graph, verified vs unverified borders |
| `docs/screenshots/career-gap.png` | Career gap with missing skills and project ideas |
| `docs/screenshots/issuer-desk.png` | Issuer queue, CSV bulk issuance, revoke with reason |
| `docs/screenshots/receipt-qr.png` | Receipt page with QR code and permalink |
| `docs/screenshots/recruiter-match.png` | Recruiter job match with verified-only score |
| `docs/screenshots/audit-log.png` | Audit log |

## Project structure

```
trustpass/
├── frontend/          React SPA (12 pages; React Flow, Recharts, QR, ethers v6)
├── backend/
│   ├── app/           FastAPI app, routers, agents, services, chain adapter
│   └── tests/         64 API tests + 23 agent tests (run with no API key)
├── blockchain/        VerifiableCredentialRegistry + 11 Hardhat tests + deploy script
├── scripts/           make.py gate runner, seed_demo.py, demo_check.py
├── data/              skills.json taxonomy (82 skills), roles.json, chain.json (generated)
├── docs/              assumptions, architecture, trust model, demo script, slides
├── Makefile + make    identical gate targets for CI and the Windows demo laptop
└── .github/workflows  CI: lint + contract + backend + frontend tests
```

## API

Interactive OpenAPI docs at `/docs` on the running backend. The response envelope is always `{"error": {"code", "message", "details"}}` on failure; trust states are the five canonical strings above.

## Trust model

Every credential shows exactly one status, and only the deterministic Integrity Agent — never an LLM — may set `Issuer-verified`, `Revoked` or `Tampered`. Details and the transition diagram: [docs/trust-model.md](docs/trust-model.md). Autonomous decisions taken while building: [docs/ASSUMPTIONS.md](docs/ASSUMPTIONS.md).

## Privacy and security

Public profiles expose only fields the student opted in to. Documents stay off-chain in local storage behind a storage-adapter interface (IPFS stub). Passwords are bcrypt-hashed, auth is JWT with role-based access, uploads are type- and size-validated, and no secrets are committed (`.env.example` holds placeholders only). The demo issuer key is Hardhat's well-known account #0 — worthless outside the local node.

## License

MIT — see [LICENSE](LICENSE).
