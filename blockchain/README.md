# Blockchain

`VerifiableCredentialRegistry` (Solidity + Hardhat). The contract itself lands in
**Stage 4** — this directory is the toolchain scaffold.

## What goes on-chain (exhaustive list)

`credentialId` · `documentHash (sha256)` · `issuerAddress` · `recipientAddress` ·
`timestamp` · `revoked`

**Never on-chain:** PDFs, images, passwords, Aadhaar or any government ID numbers,
phone numbers, emails, names. The chain is for tamper-evident credential records
only — no tokens, no trading, no speculation.

## Planned contract rules (enforced + tested in Stage 4)

| Function | Rule |
|---|---|
| `issueCredential()` | Rejects duplicate IDs; emits `CredentialIssued` |
| `verifyCredential()` | Returns recorded hash + revocation flag for comparison |
| `revokeCredential()` | **Only the original issuer** may revoke; emits `CredentialRevoked` |
| `getCredential()` | Read-only record fetch |

Required test coverage: issue · verify · revoke · unauthorized revoke · duplicate
ID · tampered hash.

## Commands (from this directory)

```bash
npm install
npx hardhat node              # local demo chain on 127.0.0.1:8545 (chainId 31337)
npx hardhat compile           # after contracts/ exists (Stage 4)
npx hardhat test              # contract tests (Stage 4)
npm run deploy:local          # deploy to the local node
```

Sepolia is configured in `hardhat.config.ts` via `SEPOLIA_RPC_URL` /
`SEPOLIA_PRIVATE_KEY` env vars but is **P2 — documented only**, not part of the
offline demo.
