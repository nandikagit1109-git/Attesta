# Slides — Attesta (DecentraHack 2.0, Round 2)

One slide per beat, ~15 seconds each when narrated.

## Slide 1 — Problem

- Certificates, projects and internships live in scattered PDFs.
- Recruiters cannot verify them; colleges verify by hand.
- Students cannot see which skills their target career actually needs.

## Slide 2 — Solution

- One credential pipeline: AI agents read evidence, issuers confirm, the SHA-256
  hash is anchored on-chain.
- Anyone verifies a file in the browser in seconds.
- Screenshot: `landing-verify.png`.

## Slide 3 — Trust model (the heart)

- Exactly one status on every credential:
  `AI-extracted (unverified)` · `Issuer-verified` · `Revoked` · `Tampered` ·
  `Unknown` (verify page only).
- AI is a suggestion, never proof. Only the deterministic Integrity Agent, plus
  an on-chain record, plus a matching hash promote a credential.
- Screenshot: `verify-diff.png`.

## Slide 4 — Live demo

- Upload, agent trace, skill graph, career gap, issuer approval, QR receipt,
  tamper failure, revoke, recruiter match.
- Follow `docs/DEMO_SCRIPT.md`; the same path is proven by `./make check`.

## Slide 5 — Architecture

- React SPA + FastAPI + 5 agents behind one orchestrator + registry contract.
- pdfplumber extraction with a Tesseract fallback; LLM wrapper with strict JSON,
  one retry, and a deterministic keyword fallback, so the demo runs offline.
- Diagram: README mermaid.

## Slide 6 — The agents

- Evidence Verification: fields + skills + flags, never claims authenticity.
- Skill Graph: maps evidence onto an 82-skill taxonomy.
- Career Mentor: verified skills weigh more; missing skills, priorities, ideas.
- Integrity: no LLM, hashes and chain state only.
- Profile: facts-only summary.
- Every run: confidence, flags, duration, fallback flag, audit row.

## Slide 7 — Why blockchain

- Multiple independent issuers write records; no single database owner.
- Tamper-evident: once anchored, nobody can quietly rewrite a hash.
- Stores only: credential ID, document hash, issuer, recipient, timestamp,
  revoked flag. No tokens, no speculation.
- Receipts re-read the transaction directly from the node in the browser, so
  Attesta's servers are not trusted either.

## Slide 8 — Impact

- Students: a shareable, provable skill identity (link and QR).
- Colleges: bulk issuance from a CSV; one approval flow instead of email chains.
- Recruiters: verified-only scoring cuts resume inflation out of shortlisting.

## Slide 9 — Revenue model

- Free for students, forever, for verified credentials.
- Issuers (colleges, bootcamps, hackathons): subscription for bulk issuance and
  analytics.
- Recruiters: paid API access to verified-skill search and job matching.
- Verification itself stays free and permissionless: it is a public good on an
  open chain.

## Slide 10 — Roadmap

- Now: local Hardhat chain, offline-capable agents, CSV bulk, receipts.
- Next: Sepolia deployment (config already included), IPFS storage adapter
  (stubbed), institution onboarding, more taxonomies.
- Later: interoperable credential schema for other registries.
