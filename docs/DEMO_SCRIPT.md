# Demo Script — Attesta (video under 3 minutes)

Record at 1080p, browser at 1440x900, zoom 110%. Keep the cursor calm; let the
app do the talking. Every step below is proven by `./make demo-check` (45
steps), so what you record is what the judges can run.

| Time | On screen | Say |
|---|---|---|
| 0:00-0:15 | Landing page, hero + verify box | "Students collect certificates their whole life, but nobody can verify them. Attesta lets AI agents read the evidence, the student approves what was extracted, the issuer confirms it, and the SHA-256 hash is anchored on-chain so anyone can check it, without trusting our servers." |
| 0:15-0:30 | Public verify: drop a random file, then the seeded verified one | "First, the no-trust check. No login. The browser hashes the file itself and asks the chain. This one is Verified, with issuer, block and transaction. This random file is honestly Not found." |
| 0:30-0:50 | One-click Student login; upload; evidence detail | "The student uploads a real certificate PDF. Five agents read it: parse, classify, extract, score confidence, summarize. Every field is labeled Unverified. It is a suggestion, never proof, until the student approves the skills." |
| 0:50-1:05 | Approve skills; skill graph; career gap | "The student approves the extracted skills. The skill graph builds itself: dashed border means unverified, double border with the Verified label means an issuer proved it. Against Data Analyst, a gap score with project ideas; verified skills count in full, unverified at forty percent." |
| 1:05-1:25 | One-click Issuer login; queue shows only approved; confirm | "The issuer sees only evidence the student approved. Confirming computes the SHA-256 server-side and writes it to the registry contract. The integrity module re-checks: record exists, hash matches, not revoked. Verified." |
| 1:25-1:40 | Receipt page with QR; student dashboard share link | "A shareable receipt with a QR code, and the student publishes one share link for recruiters. Anyone can open it with no account, and the receipt re-reads the issuance transaction straight from the node with ethers, right in the browser." |
| 1:40-1:55 | One-click Admin login; Reset demo data; One-click tamper | "Now the failure case. The demo admin flips one byte in a stored copy of the certificate." |
| 1:55-2:15 | Credential page HASH MISMATCH; verify the tampered copy | "The credential page shows HASH MISMATCH immediately, with the changed hex characters highlighted. The on-chain record stays untouched; the registry cannot be edited, which is exactly the point. An off-chain tamper-detection entry lands in the audit log." |
| 2:15-2:30 | Issuer revokes with a reason; public verify shows Revoked | "The issuer can revoke with a reason. The public verify page shows Revoked, with the reason and timestamp, for everyone." |
| 2:30-2:50 | Open the share link as a guest; skills, proof, job match | "The recruiter opens the share link. No login, no directory, nothing to enumerate. Status per credential, skill cards with confidence, on-chain proof. They paste a job description; the score counts verified skills only." |
| 2:50-3:00 | Public audit log page, hold on architecture slide | "The audit log is public: chain events plus off-chain tamper entries, hashes and addresses only. AI for reading, students for consent, issuers for truth, the chain for proof." |

Recording checklist:

- `./make demo-check` passes before recording; the node is running (`./make chain`).
- Seed fresh (`./make seed` or the admin's Reset demo data button) so the numbers on screen match this script.
- The tampered copy is pre-staged on the seeded Python credential; the admin's one-click tamper produces it.
- If a step misbehaves live, the admin's Reset demo data button restores the exact seeded state in one click.
