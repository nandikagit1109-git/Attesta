# Trust Model

Attesta has exactly **five** trust states. Every UI label and API response uses one of them — no synonyms, no sixth state. Canonical source: [backend/app/states.py](../backend/app/states.py).

| State | Meaning | Who/what may set it |
|---|---|---|
| `AI-extracted (unverified)` | A suggestion extracted from a document by the agents. **Never proof of authenticity.** | Evidence Verification Agent, Skill Graph Agent |
| `Issuer-verified` | On-chain record exists **AND** document hash matches the anchored hash **AND** not revoked. All three, together. | Integrity Agent only |
| `Revoked` | The original issuer revoked the credential. Reason and timestamp are public. | Integrity Agent only |
| `Tampered` | A presented hash differs from the anchored hash. | Integrity Agent only |
| `Unknown` | A hash is not anchored on-chain at all. Verify page only. | verify endpoint |

## State transitions

```
                          upload + analyze
        Document ─────────────────────────────▶ AI-extracted (unverified)
                                                     │
                                        issuer issues issueCredential()
                                                     ▼
                                              Issuer-verified
                                                     │
                          revokeCredential()  ┌──────┴─────────┐
                    presented hash ≠ anchored ▼                ▼
                                              Revoked      Tampered
```

Rules:

- `AI-extracted (unverified)` never promotes itself. Only an issuer's on-chain record promotes it.
- "Verified" is **conjunction**: on-chain record ∧ hash matches ∧ not revoked. A missing piece is not verified.
- Only the Integrity Agent (deterministic code, no LLM) decides `Issuer-verified`, `Revoked` and `Tampered`.
- A bare hash that matches nothing reports `Unknown`. It is deliberately not guessed into `Tampered`: the server never pretends to know what an unmatched file "used to be". `Tampered` is earned by checking a presented hash **against a specific credential** (the receipt permalink / QR flow passes `credential_id`).

## Agent claims vs. facts

| Agent | May claim | May never claim |
|---|---|---|
| Evidence Verification | "These fields were extracted with confidence X; flags: name mismatch, future date…" | "This document is authentic" |
| Skill Graph | "Evidence maps to skill nodes with strength Y" | That the mapping is authoritative truth |
| Career Mentor | "For role R you lack skills S; here are project ideas" | That unverified skills are proven |
| Integrity | "On-chain record exists / hash differs / issuer revoked it" | Anything about document content |
| Profile | "Facts on the profile, summarized" | Claims beyond profile facts |

## Why a blockchain at all

Several independent issuers write records, and anyone can verify without trusting Attesta's servers. The chain stores only: credential ID, document hash, issuer address, recipient address, timestamp, revoked flag. No tokens, no trading, no speculation. Receipts re-read the issuance transaction directly from the node in the browser (ethers.js), so even the API's honesty is not required for a verdict.
