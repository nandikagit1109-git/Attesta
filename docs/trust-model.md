# Trust Model

TrustPass has exactly **three** trust states. Every UI label and API response uses one of them — no synonyms, no fourth state.

## The three states

| State | Meaning | Who/what may set it |
|---|---|---|
| `AI-extracted (unverified)` | A suggestion extracted from a document by the LLM/OCR pipeline. **Never proof of authenticity.** | Evidence Verification Agent, Skill Graph Agent |
| `Issuer-verified` | Issuer-signed on-chain record **AND** document hash matches the anchored hash **AND** not revoked. All three, together. | Integrity Agent only |
| `Revoked or tampered` | Revoked on-chain, or the stored document hash differs from the on-chain hash. | Integrity Agent only |

## State transitions

```
                          upload + analyze
        Document ─────────────────────────────▶ AI-extracted (unverified)
                                                     │
                                        issuer signs issueCredential()
                                                     ▼
                                              Issuer-verified
                                                     │
                          revokeCredential()  ┌──────┴─────────┐
                    document replaced/edited  ▼                ▼
                                        Revoked or tampered
```

Rules:

- `AI-extracted (unverified)` never promotes itself. Only an issuer signature on-chain promotes it.
- "Verified" is **conjunction**: signature present ∧ hash matches ∧ not revoked. A missing piece is not verified.
- Only the Integrity Agent (deterministic code, no LLM) decides `Issuer-verified` / `Revoked or tampered`. No other component computes trust state.

## Agent claims vs. facts

| Agent | May claim | May never claim |
|---|---|---|
| Evidence Verification | "These fields were extracted with confidence X; flags: name mismatch, future date…" | "This document is authentic" |
| Skill Graph | "Evidence maps to skill nodes with strength Y" | That mapping is authoritative truth |
| Career Mentor | "For role R you lack skills S; here are project ideas" | That unverified skills are proven |
| Integrity | "match / mismatch / revoked, with reasons" | Anything beyond hash + revocation facts |
| Profile | Summary using **only** facts present in the profile | Invented achievements |

## Why blockchain

Multiple **independent** issuers (a college, a company, a hackathon organizer) write credential records. A recruiter verifying a student's passport should not have to trust TrustPass's servers, our database, or any single owner of the data. Anchoring SHA-256 document hashes on-chain gives:

1. **Tamper-evidence** — once written, a credential record can't be quietly rewritten (revocation is an explicit, issuer-only transaction).
2. **Issuer independence** — no consortium database to trust; each issuer signs from its own key.
3. **Recruiter sovereignty** — anyone with a node/RPC can re-check a hash and revocation flag.

Scope discipline: the chain is used **only** for tamper-evident credential records. No tokens, no trading, no speculation.

## On-chain data (exhaustive)

`credentialId`, `documentHash (sha256)`, `issuerAddress`, `recipientAddress`, `timestamp`, `revoked`.

Never on-chain: PDFs, images, passwords, Aadhaar or any government ID numbers, phone numbers, emails, names.

## Privacy boundaries

- Public profiles expose only fields the student explicitly opted in to.
- Documents live off-chain, behind a storage-adapter interface (local disk now; IPFS/Supabase adapters stubbed, P2).
- Auth: bcrypt password hashing + JWT. Files validated by type and size before storage.
