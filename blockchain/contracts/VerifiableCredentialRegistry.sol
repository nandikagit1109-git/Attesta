// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

/**
 * @title VerifiableCredentialRegistry
 * @notice Attesta's tamper-evident anchor. Anyone can check a credential
 *         without trusting Attesta's servers.
 * @dev Stores ONLY: credentialId, docHash (SHA-256), issuer, recipient,
 *      timestamps, revoked flag and revoke reason. No PII beyond the two
 *      addresses, no tokens, nothing speculative.
 */
contract VerifiableCredentialRegistry {
    /// Verification outcome for a presented document hash.
    enum Status {
        Unknown,  // id was never issued on this registry
        Valid,    // record exists, not revoked, hash matches exactly
        Tampered, // record exists but the presented hash differs from the issued one
        Revoked   // the original issuer revoked this credential
    }

    struct Credential {
        bytes32 docHash;      // SHA-256 of the document, issued by the issuer
        address issuer;       // who anchored the record (only they may revoke)
        address recipient;    // wallet address generated for the student
        uint64 issuedAt;      // seconds since epoch
        uint64 revokedAt;     // 0 while not revoked
        string revokeReason;  // empty while not revoked
        bool revoked;
        bool exists;
    }

    mapping(bytes32 => Credential) private credentials;
    bytes32[] private credentialIds;

    event CredentialIssued(
        bytes32 indexed credentialId,
        bytes32 indexed docHash,
        address indexed issuer,
        address recipient,
        uint64 issuedAt
    );
    event CredentialRevoked(
        bytes32 indexed credentialId,
        address indexed revokedBy,
        string reason,
        uint64 revokedAt
    );

    error DuplicateCredentialId(bytes32 credentialId);
    error NotOriginalIssuer(address caller, address issuer);
    error CredentialNotFound(bytes32 credentialId);
    error AlreadyRevoked(bytes32 credentialId);
    error InvalidRecipient();

    /// Anchor a credential. Duplicate ids are rejected so a credential can
    /// only ever be issued once.
    function issueCredential(bytes32 credentialId, bytes32 docHash, address recipient) external {
        if (recipient == address(0)) revert InvalidRecipient();
        if (credentials[credentialId].exists) revert DuplicateCredentialId(credentialId);
        uint64 ts = uint64(block.timestamp);
        credentials[credentialId] = Credential({
            docHash: docHash,
            issuer: msg.sender,
            recipient: recipient,
            issuedAt: ts,
            revokedAt: 0,
            revokeReason: "",
            revoked: false,
            exists: true
        });
        credentialIds.push(credentialId);
        emit CredentialIssued(credentialId, docHash, msg.sender, recipient, ts);
    }

    /// Compare a presented document hash with the anchored one.
    /// Revocation dominates: a revoked credential reports Revoked even if the
    /// hash still matches, because the issuer has withdrawn it.
    function verifyCredential(bytes32 credentialId, bytes32 docHash) external view returns (Status) {
        Credential storage c = credentials[credentialId];
        if (!c.exists) return Status.Unknown;
        if (c.revoked) return Status.Revoked;
        if (c.docHash != docHash) return Status.Tampered;
        return Status.Valid;
    }

    /// Revoke with a public reason. Only the original issuer may do this,
    /// and only once.
    function revokeCredential(bytes32 credentialId, string calldata reason) external {
        Credential storage c = credentials[credentialId];
        if (!c.exists) revert CredentialNotFound(credentialId);
        if (c.issuer != msg.sender) revert NotOriginalIssuer(msg.sender, c.issuer);
        if (c.revoked) revert AlreadyRevoked(credentialId);
        uint64 ts = uint64(block.timestamp);
        c.revoked = true;
        c.revokedAt = ts;
        c.revokeReason = reason;
        emit CredentialRevoked(credentialId, msg.sender, reason, ts);
    }

    /// Full record for a credential id (reverts if never issued).
    function getCredential(bytes32 credentialId) external view returns (Credential memory) {
        if (!credentials[credentialId].exists) revert CredentialNotFound(credentialId);
        return credentials[credentialId];
    }

    /// Number of credentials ever issued on this registry.
    function totalCredentials() external view returns (uint256) {
        return credentialIds.length;
    }
}
