import { expect } from "chai";
import { ethers } from "hardhat";

/**
 * Contract tests for VerifiableCredentialRegistry. These cover every rule the
 * trust model depends on: issue, verify (valid / tampered / unknown), revoke
 * (original issuer only, once, with reason), duplicate rejection, and field
 * integrity of the stored record.
 */
describe("VerifiableCredentialRegistry", () => {
  const CREDENTIAL_ID = ethers.id("credential-1"); // bytes32 id, keccak256 here
  const DOC_HASH = ethers.sha256(ethers.toUtf8Bytes("python-certificate.pdf"));

  async function deployRegistry() {
    const [issuer, other, recipient] = await ethers.getSigners();
    const factory = await ethers.getContractFactory("VerifiableCredentialRegistry");
    const registry = await factory.deploy();
    await registry.waitForDeployment();
    return { registry, issuer, other, recipient };
  }

  async function issueFrom(registry: any, issuer: any, recipient: any) {
    const tx = await registry
      .connect(issuer)
      .issueCredential(CREDENTIAL_ID, DOC_HASH, recipient.address);
    const receipt = await tx.wait();
    return { tx, receipt };
  }

  it("issues a credential and stores every field", async () => {
    const { registry, issuer, recipient } = await deployRegistry();
    const { receipt } = await issueFrom(registry, issuer, recipient);

    expect(await registry.totalCredentials()).to.equal(1);

    const c = await registry.getCredential(CREDENTIAL_ID);
    expect(c.docHash).to.equal(DOC_HASH);
    expect(c.issuer).to.equal(issuer.address);
    expect(c.recipient).to.equal(recipient.address);
    expect(c.exists).to.equal(true);
    expect(c.revoked).to.equal(false);
    expect(c.revokedAt).to.equal(0);
    expect(c.revokeReason).to.equal("");
    expect(Number(c.issuedAt)).to.be.greaterThan(0);

    // The block number recorded for the issue transaction is available to
    // off-chain UIs via the receipt.
    expect(receipt!.blockNumber).to.be.greaterThan(0);
  });

  it("emits CredentialIssued with all indexed arguments", async () => {
    const { registry, issuer, recipient } = await deployRegistry();
    await expect(
      registry.connect(issuer).issueCredential(CREDENTIAL_ID, DOC_HASH, recipient.address),
    )
      .to.emit(registry, "CredentialIssued")
      .withArgs(CREDENTIAL_ID, DOC_HASH, issuer.address, recipient.address, anyUint());
  });

  it("verifyCredential returns Valid for the exact issued hash", async () => {
    const { registry, issuer, recipient } = await deployRegistry();
    await issueFrom(registry, issuer, recipient);
    expect(await registry.verifyCredential(CREDENTIAL_ID, DOC_HASH)).to.equal(1n); // Valid
  });

  it("verifyCredential returns Tampered when the presented hash differs by one bit", async () => {
    const { registry, issuer, recipient } = await deployRegistry();
    await issueFrom(registry, issuer, recipient);
    // Flip one byte of the original hash: the smallest possible tamper.
    const bytes = ethers.getBytes(DOC_HASH);
    bytes[0] = bytes[0] ^ 0x01;
    const tamperedHash = ethers.hexlify(bytes);
    expect(tamperedHash).to.not.equal(DOC_HASH);
    expect(await registry.verifyCredential(CREDENTIAL_ID, tamperedHash)).to.equal(2n); // Tampered
  });

  it("verifyCredential returns Unknown for a credential that was never issued", async () => {
    const { registry } = await deployRegistry();
    expect(await registry.verifyCredential(ethers.id("nope"), DOC_HASH)).to.equal(0n); // Unknown
  });

  it("rejects duplicate credential IDs", async () => {
    const { registry, issuer, recipient } = await deployRegistry();
    await issueFrom(registry, issuer, recipient);
    await expect(
      registry.connect(issuer).issueCredential(CREDENTIAL_ID, DOC_HASH, recipient.address),
    ).to.be.revertedWithCustomError(registry, "DuplicateCredentialId");
  });

  it("allows only the original issuer to revoke", async () => {
    const { registry, issuer, other, recipient } = await deployRegistry();
    await issueFrom(registry, issuer, recipient);
    await expect(
      registry.connect(other).revokeCredential(CREDENTIAL_ID, "not my credential"),
    ).to.be.revertedWithCustomError(registry, "NotOriginalIssuer");
  });

  it("revocation sets flag, reason, timestamp, emits the event and verification then reports Revoked", async () => {
    const { registry, issuer, recipient } = await deployRegistry();
    await issueFrom(registry, issuer, recipient);

    const reason = "document proven fraudulent";
    await expect(registry.connect(issuer).revokeCredential(CREDENTIAL_ID, reason))
      .to.emit(registry, "CredentialRevoked")
      .withArgs(CREDENTIAL_ID, issuer.address, reason, anyUint());

    const c = await registry.getCredential(CREDENTIAL_ID);
    expect(c.revoked).to.equal(true);
    expect(c.revokeReason).to.equal(reason);
    expect(Number(c.revokedAt)).to.be.greaterThan(0);

    // Revoked dominates even when the presented hash still matches.
    expect(await registry.verifyCredential(CREDENTIAL_ID, DOC_HASH)).to.equal(3n); // Revoked
  });

  it("cannot revoke twice", async () => {
    const { registry, issuer, recipient } = await deployRegistry();
    await issueFrom(registry, issuer, recipient);
    await registry.connect(issuer).revokeCredential(CREDENTIAL_ID, "first");
    await expect(
      registry.connect(issuer).revokeCredential(CREDENTIAL_ID, "second"),
    ).to.be.revertedWithCustomError(registry, "AlreadyRevoked");
  });

  it("cannot revoke or read a credential that was never issued", async () => {
    const { registry, issuer } = await deployRegistry();
    const ghost = ethers.id("ghost");
    await expect(registry.connect(issuer).revokeCredential(ghost, "ghost"))
      .to.be.revertedWithCustomError(registry, "CredentialNotFound");
    await expect(registry.getCredential(ghost))
      .to.be.revertedWithCustomError(registry, "CredentialNotFound");
  });

  it("rejects the zero address as recipient", async () => {
    const { registry, issuer } = await deployRegistry();
    await expect(
      registry
        .connect(issuer)
        .issueCredential(CREDENTIAL_ID, DOC_HASH, ethers.ZeroAddress),
    ).to.be.revertedWithCustomError(registry, "InvalidRecipient");
  });
});

/** Match helper for the uint64 issuedAt/revokedAt timestamps we do not pin. */
function anyUint() {
  return (value: unknown) => typeof value === "bigint" && value >= 0n;
}
