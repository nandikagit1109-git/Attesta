# Demo Script — Attesta (video under 3 minutes)

Record at 1080p, browser at 1440x900, zoom 110%. Keep the cursor calm; let the
app do the talking. Every step below is proven by `./make check`, so what you
record is what the judges can run. No em dashes in on-screen copy; the app
already follows the flat design rules.

| Time | On screen | Say |
|---|---|---|
| 0:00-0:15 | Landing page, hero + verify box | "Students collect certificates their whole life, but nobody can verify them. Attesta lets AI agents read the evidence, issuers confirm it, and the SHA-256 hash is anchored on-chain so anyone can check it, without trusting our servers." |
| 0:15-0:30 | Click "Enter the demo", login page, one click "Student" | "One-click demo login. The student uploads a real certificate PDF." |
| 0:30-0:50 | Dashboard upload; evidence detail | "The agents read it: title, issuer, name, date, and the skills it proves. Every field is clearly labeled AI-extracted, unverified. It is a suggestion, never proof. Here is the full agent trace: input, output, confidence, duration, and whether the deterministic fallback ran." |
| 0:50-1:05 | Skill graph page | "The skill graph builds itself. Dashed border means unverified; double border with the verified label means an issuer proved it. Never color alone." |
| 1:05-1:20 | Career gap page | "Against the Data Analyst role: a score, what is missing, by priority, and three project ideas to close the gap. Verified skills count in full, unverified ones at forty percent." |
| 1:20-1:45 | Log out, one click "Issuer", queue, "Approve and anchor on-chain" | "The college issuer reviews the queue and approves. The document's SHA-256 is written to the registry contract. The integrity agent immediately re-checks: record exists, hash matches, not revoked. Issuer-verified." |
| 1:45-2:00 | Receipt page with QR | "A shareable receipt with a QR code. Anyone can open it and re-read the issuance transaction straight from the node with ethers, right in the browser." |
| 2:00-2:20 | Receipt file checker: drop the tampered copy | "Now the failure case. This copy was modified after issuance: one flipped byte. The browser hashes it and the verdict is Tampered, with the changed hex characters highlighted." |
| 2:20-2:35 | Issuer desk, revoke with reason, then public verify shows Revoked | "The issuer can revoke with a reason. The public verify page shows Revoked, with the reason and timestamp, for everyone." |
| 2:35-2:50 | Recruiter: directory, paste JD, job match | "For recruiters: search candidates, paste a job description. The score counts issuer-verified skills only; unverified matches are listed separately and never inflate the score." |
| 2:50-3:00 | Audit log page, hold on architecture slide | "Every issue, revoke, verify and agent run is logged. AI for reading, issuers for truth, the chain for proof." |

Recording checklist:

- `./make check` passes before recording; the node is running (`./make chain`).
- Seed fresh (`./make seed` or the Reset demo data button) so the numbers on screen match this script.
- The tampered copy: evidence page, "Tamper with this file (demo)", then "Download tampered copy"; drop that file on the receipt page.
- If a step misbehaves live, the Reset demo data button restores the exact seeded state in one click.
