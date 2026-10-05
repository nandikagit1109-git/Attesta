# Trust Model

Attesta has exactly **five** trust states. Every UI label and API response uses one of them — no synonyms, no sixth state. Canonical source: [backend/app/states.py](../backend/app/states.py).

| State | Meaning | Who/what may set it |
|---|---|---|
| `Unverified` | Extracted from a document by the agents, or awaiting the student's skill approval and the issuer's confirmation. **Never proof of authenticity.** | Agents, issuer queue |
| `Verified` | On-chain record exists **AND** document hash matches the anchored hash **AND** not revoked. All three, together. | Integrity module only |
| `Revoked` | The original issuer revoked the credential. Reason and timestamp are public. | Integrity module only |
| `Tampered` | A presented hash differs from the anchored hash for a specific credential. | Integrity module only |
| `Not found` | A hash is anchored nowhere on the registry. Public verify page only. | verify endpoint |

## State transitions

```
                            upload + analyze
        Document ─────────────────────────────▶ Unverified
                                                     │
                                     student approves the skills
                                                     │
                                     issuer issues issueCredential()
                                                     ▼
                                                 Verified
                                                     │
                          revokeCredential()  ┌──────┴─────────┐
                    presented hash ≠ anchored ▼                ▼
                                                Revoked      Tampered

        bare hash anchored nowhere ───────────▶ Not found (verify page only)
```

Rules:

- `Unverified` never promotes itself. The student must approve the extracted skills, and only an issuer's on-chain record promotes the credential.
- "Verified" is **conjunction**: on-chain record ∧ hash matches ∧ not revoked. A missing piece is not verified.
- Only the deterministic Integrity module (plain code, no LLM) decides `Verified`, `Revoked` and `Tampered`.
- A bare hash that anchors nothing reports `Not found`. It is deliberately not guessed into `Tampered`: the server never pretends to know what an unmatched file "used to be". `Tampered` is earned by checking a presented hash **against a specific credential** — via the optional credential-ID field on the public verify page, the receipt permalink, or the QR flow, all of which pass `credential_id`.

## Agents' claims vs. facts

| Agent | May claim | May never claim |
|---|---|---|
| Document Parser | "These fields were parsed from the document" | That the document is authentic |
| Skill Classifier / Extractor | "Evidence maps to these taxonomy skills with confidence X" | That the mapping is authoritative truth |
| Confidence Scorer | "Extraction confidence is X because Y" | That unverified skills are proven |
| Profile Summarizer | "A summary built only from profile facts" | Claims beyond the facts |
| Integrity (no LLM) | "On-chain record exists / hash differs / issuer revoked it" | Anything about document content |

## Recruiters are guests

Recruiters never log in and can never enumerate profiles or files. A student publishes exactly one long random share token (`POST /api/profile/share-link`); the guest opens `/s/<token>` or scans its QR code and sees only what that student published: status per credential, skill cards with confidence, on-chain proof (hash, transaction, block, timestamp, issuer address) and the agent trace. There is no directory, no search endpoint, and no file downloads. Unknown tokens return 404.

## Why a blockchain at all

Several independent issuers write records, and anyone can verify without trusting Attesta's servers. The chain stores only: credential ID, document hash, issuer address, recipient address, timestamp, revoked flag. No tokens, no trading, no speculation. The registry keeps a reverse index from document hash back to credential ID, so a bare file hash is enough to find its record. Receipts re-read the issuance transaction directly from the node in the browser (ethers.js), so even the API's honesty is not required for a verdict.
