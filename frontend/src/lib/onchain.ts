/**
 * Direct on-chain reads with ethers v6 (verify without trusting Attesta's
 * servers). The browser calls the local Hardhat / configured RPC itself and
 * decodes the registry response. Every failure degrades to `error` so the
 * page keeps working when the node is simply not reachable.
 */

import { Contract, JsonRpcProvider } from "ethers";
import type { ChainInfo } from "./types";
import { apiGet } from "./api";

const REGISTRY_ABI = [
  "function getCredential(bytes32) view returns (bytes32,bytes32,address,address,uint64,bool,string)",
];

export interface OnchainRecord {
  docHash: string;
  issuer: string;
  recipient: string;
  timestamp: number;
  revoked: boolean;
  revokeReason: string;
}

export async function fetchChainInfo(): Promise<ChainInfo | null> {
  try {
    return await apiGet<ChainInfo>("/api/chain");
  } catch {
    return null;
  }
}

/** Read one credential straight from the registry contract. */
export async function readOnchain(
  chainCredId: number,
  info: ChainInfo,
): Promise<OnchainRecord | { error: string }> {
  try {
    const provider = new JsonRpcProvider(info.rpc_url, info.chain_id, { staticNetwork: true });
    const registry = new Contract(info.contract_address, REGISTRY_ABI, provider);
    const id32 = "0x" + chainCredId.toString(16).padStart(64, "0");
    const rec = (await registry.getCredential(id32)) as [string, string, string, string, bigint, boolean, string];
    return {
      docHash: rec[1],
      issuer: rec[2],
      recipient: rec[3],
      timestamp: Number(rec[4]),
      revoked: rec[5],
      revokeReason: rec[6],
    };
  } catch {
    return { error: "Direct chain read unavailable from this browser." };
  }
}

export interface TxReceiptSummary {
  hash: string;
  blockNumber: number;
  status: number;
  to: string;
  from: string;
  logCount: number;
}

/** Re-read the issuance transaction itself, straight from the node. */
export async function readTxReceipt(txHash: string, info: ChainInfo): Promise<TxReceiptSummary | { error: string }> {
  try {
    const provider = new JsonRpcProvider(info.rpc_url, info.chain_id, { staticNetwork: true });
    const receipt = await provider.getTransactionReceipt(txHash);
    if (!receipt) return { error: "Transaction not found on this node yet." };
    return {
      hash: receipt.hash,
      blockNumber: receipt.blockNumber,
      status: receipt.status ?? 0,
      to: receipt.to ?? "",
      from: receipt.from,
      logCount: receipt.logs.length,
    };
  } catch {
    return { error: "Direct chain read unavailable from this browser." };
  }
}
