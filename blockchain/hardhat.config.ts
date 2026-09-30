import * as dotenv from "dotenv";
dotenv.config();

import { HardhatUserConfig } from "hardhat/config";
import "@nomicfoundation/hardhat-toolbox";

/**
 * TrustPass chain config.
 * - Default: in-process Hardhat network for tests.
 * - `npx hardhat node` + network "localhost": demo chain (no real money, ever).
 * - "sepolia" is P2: documented as a switch, not part of the offline demo.
 *
 * The registry stores ONLY: credentialId, docHash, issuer, recipient,
 * timestamp, revoked. No PII, no tokens, no trading.
 */

const SEPOLIA_RPC_URL = process.env.SEPOLIA_RPC_URL ?? "";
const SEPOLIA_PRIVATE_KEY = process.env.SEPOLIA_PRIVATE_KEY ?? "";

const config: HardhatUserConfig = {
  solidity: {
    version: "0.8.24",
    settings: {
      optimizer: { enabled: true, runs: 200 },
    },
  },
  networks: {
    hardhat: {
      chainId: 31337,
    },
    localhost: {
      url: "http://127.0.0.1:8545",
      chainId: 31337,
    },
    sepolia: {
      // P2 — documented only. Requires SEPOLIA_RPC_URL + SEPOLIA_PRIVATE_KEY.
      url: SEPOLIA_RPC_URL || "https://rpc.sepolia.org",
      accounts: SEPOLIA_PRIVATE_KEY ? [SEPOLIA_PRIVATE_KEY] : [],
    },
  },
};

export default config;
