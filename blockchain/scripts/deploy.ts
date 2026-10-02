import { network, ethers } from "hardhat";
import * as fs from "fs";
import * as path from "path";

/**
 * Deploy VerifiableCredentialRegistry and write the result to the shared
 * config at data/chain.json, which the backend reads when CONTRACT_ADDRESS is
 * not set in the environment. Runs against the local Hardhat node for the
 * demo; Sepolia works too when the network env vars are configured.
 */
async function main() {
  const [deployer] = await ethers.getSigners();
  const factory = await ethers.getContractFactory("VerifiableCredentialRegistry");
  const registry = await factory.deploy();
  await registry.waitForDeployment();

  const address = await registry.getAddress();
  const chainId = Number((await ethers.provider.getNetwork()).chainId);

  const shared = {
    network: network.name,
    chainId,
    contractAddress: address,
    deployer: deployer.address,
    deployedAt: new Date().toISOString(),
  };

  // data/ is two levels up from blockchain/scripts/
  const dataDir = path.resolve(__dirname, "..", "..", "data");
  fs.mkdirSync(dataDir, { recursive: true });
  const configPath = path.join(dataDir, "chain.json");
  fs.writeFileSync(configPath, JSON.stringify(shared, null, 2) + "\n");

  console.log(`VerifiableCredentialRegistry deployed at ${address}`);
  console.log(`network=${shared.network} chainId=${chainId} deployer=${deployer.address}`);
  console.log(`shared config written: ${configPath}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
