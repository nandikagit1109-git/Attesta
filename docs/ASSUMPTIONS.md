# ASSUMPTIONS

Decisions taken autonomously while building Attesta. Each entry says what was
assumed and why. If any assumption is wrong, it is cheap to reverse.

## Product and repo

1. **Repo strategy: evolve `trustpass/` in place, rebrand to Attesta.**
   The repo already has a working Vercel deployment (frontend
   `trustpass-frontend.vercel.app`, backend `trustpass-backend-api.vercel.app`)
   with auto-redeploy on push. Rebuilding in a fresh repo would throw away
   that wiring. So: rebrand all user-visible strings to Attesta, keep the
   directory name and the Vercel plumbing (backend/api/index.py, legacy
   `routes` vercel.json, VercelPathRewriteMiddleware). The unrelated
   `trustpass-api` Vercel project in the team is never touched.
2. **Trust-state wording updated to the Attesta spec.** Four statuses now:
   `AI-extracted (unverified)`, `Issuer-verified`, `Revoked` (with reason and
   timestamp), `Tampered` (with reason), plus `Unknown` which only appears on
   the public verify page when a hash is not on-chain. The old combined
   "Revoked or tampered" is retired. Backend `states.py` and frontend
   `trustStates.ts` stay mirrors of each other.
3. **`make` is not installed on the demo laptop (Windows, Git Bash only).**
   The `Makefile` is canonical for CI (GitHub Actions runs real `make`) and
   for Linux/Mac judges. On this laptop the same targets run through
   `scripts/make.py` via the `./make` wrapper: `./make test-contracts`,
   `./make test-backend`, `./make build`, `./make check`. Both files list
   identical targets; the Makefile delegates to the Python runner so the two
   can never drift.
4. **Python: always `backend/.venv` (3.11.9).** The system python3 is 3.14 and
   has none of the deps. The make runner resolves the venv interpreter
   automatically; CI uses the system python.
5. **Node 24 / npm 11 are fine for Hardhat 2.22 and Vite 6.** Nothing needs
   downgrading.

## Blockchain

6. **Demo chain is Hardhat, started and deployed automatically.** The backend
   `ensure_chain()` routine starts `npx hardhat node` (detached) if the RPC
   is unreachable, then runs the deploy script, which writes the address to
   `data/chain.json` (the shared config) and returns it. The backend reads
   `CONTRACT_ADDRESS` env first, then `data/chain.json`. Sepolia stays an
   optional env-only switch.
7. **Issuer signing uses a well-known Hardhat test key.** For the local chain
   (id 31337) the backend falls back to Hardhat's account #0 key when
   `DEMO_ISSUER_PRIVATE_KEY` is empty. That key is public, printed in every
   Hardhat install, and worthless on any real network; it is documented in
   `.env.example` rather than being treated as a secret. A real key is never
   committed.
8. **Wallet-less students:** the backend generates a fresh Ethereum keypair
   per student at signup and stores the address (plus the demo private key,
   marked demo-only) so credentials can be issued to real addresses with no
   MetaMask. MetaMask remains optional and unused in the demo.
9. **Chain stores only:** credentialId (bytes32), docHash (bytes32 SHA-256),
   issuer, recipient, timestamp, revoked flag + revoke reason. No PII beyond
   addresses, no tokens, no speculation.
10. **The hosted Vercel backend has no chain access.** Serverless cannot keep
    a local node, so on the hosted deployment chain-dependent endpoints
    return the standard `CHAIN_ERROR` envelope and evidence stays
    `AI-extracted (unverified)`. The offline demo on the laptop runs the full
    on-chain path; the hosted deployment demonstrates the rest. This is a
    hosting-environment fact, not a product limitation.

## Backend

11. **SQLite remains the default; PostgreSQL via `DATABASE_URL`.** The hosted
    SQLite is ephemeral (serverless `/tmp`), which is acceptable for the
    hosted preview; the laptop demo uses a file DB and the seed script
    rebuilds demo state deterministically.
12. **LLM layer is optional by design.** With `LLM_*` env empty, all five
    agents run on the deterministic keyword + taxonomy fallback and the whole
    demo works offline. With a key present, the wrapper calls any
    OpenAI-compatible endpoint with strict JSON validation and one retry,
    then falls back on any failure.
13. **Uploads stay local** under `backend/uploads` (gitignored) behind a
    storage-adapter interface with an IPFS stub, per spec.
14. **File limits:** PDF/PNG/JPG/JPEG only, 10 MB max, enforced at the API
    layer; hashing is SHA-256 over raw bytes (browser Web Crypto on the
    public page, hashlib on the backend, and the two must agree).

## Frontend

15. **Design system is the Attesta flat editorial palette** (#EFE7D6 /
    #E4D8C0 / #2E1F14 / #B4451F / #C8922A, Fraunces + IBM Plex Sans + IBM
    Plex Mono, 1px #2E1F14 borders, radius <= 2px). The old TrustPass
    Tailwind palette (amber/emerald/rose trust colors) is replaced; verified
    vs unverified nodes differ by border style and label, not color alone.
16. **Fonts are loaded via Google Fonts** with system serif/sans/mono
    fallbacks, so the demo still works fully offline with graceful fallback
    typography if fonts fail to load.
17. **React Router v6 with `BrowserRouter`** is kept; the Vercel SPA rewrite
    already handles deep links (verified: deep routes return 200).

## Process

18. **Each phase ends at its gate before the next begins:** Phase 1
    `test-contracts`, Phase 2 `test-backend`, Phase 3 agent tests with no API
    key, Phase 4 `build`, Phase 5 `check`, Phase 6 CI green. Failures are
    fixed before moving on; only true blockers would interrupt the user.
19. **Git:** work continues on `main`. Commits happen per phase with the
    existing trailer style. No force-push, no deploys beyond the already
    wired auto-redeploy on push.
