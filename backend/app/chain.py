"""Blockchain adapter for the VerifiableCredentialRegistry.

Design rules:
- web3 imports lazily, so the serverless deployment (no chain extras) still
  boots and chain endpoints return a clean CHAIN_ERROR.
- The local Hardhat node is started automatically when unreachable, and the
  contract is deployed automatically, with the address recorded in the shared
  config data/chain.json (written by blockchain/scripts/deploy.ts).
- The issuer signs with a demo-only key from settings (Hardhat account #0 by
  default). See docs/ASSUMPTIONS.md #7.
"""

import json
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from .config import get_settings

settings = get_settings()

LOCAL_HOSTS = ("127.0.0.1", "localhost", "0.0.0.0")

_lock = threading.Lock()
_cache: dict[str, tuple[Any, Any]] = {}  # key: (rpc_url, contract_address) -> (w3, contract)


class ChainError(Exception):
    """Raised when the chain is unreachable, undeployed or rejects a tx."""


def _repo_root() -> Path:
    return (Path(__file__).resolve().parent / settings.repo_root).resolve()


def _npx() -> str:
    import os
    import shutil

    name = "npx.cmd" if os.name == "nt" else "npx"
    return shutil.which(name) or name


def _spawn_detached(cmd: list[str], cwd: Path, log_path: Path) -> None:
    import os

    log_path.parent.mkdir(parents=True, exist_ok=True)
    log = open(log_path, "ab")
    kwargs: dict[str, Any] = {}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(cmd, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, **kwargs)


def _read_shared_config() -> str:
    path = Path(settings.resolve(settings.chain_config_path))
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8")).get("contractAddress", "")
        except (OSError, ValueError):
            return ""
    return ""


def _load_abi() -> list[dict]:
    path = Path(settings.resolve(settings.chain_abi_path))
    if not path.exists():
        raise ChainError(
            "Contract ABI not found; run the blockchain build first (./make chain)."
        )
    artifact = json.loads(path.read_text(encoding="utf-8"))
    return artifact["abi"]


def _node_modules_ready() -> bool:
    return (_repo_root() / "blockchain" / "node_modules" / ".package-lock.json").exists()


def _wait_for_rpc(url: str, w3_factory, seconds: int = 90) -> Any:
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            w3 = w3_factory(url)
            if w3.is_connected():
                return w3
        except Exception:  # noqa: S110 - polling loop, retried until the deadline
            pass
        time.sleep(1.5)
    return None


def _deploy() -> str:
    """Run the Hardhat deploy script; returns the deployed address."""
    blockchain_dir = _repo_root() / "blockchain"
    env_host = settings.chain_rpc_url.split("//")[-1].split(":")[0]
    network = "localhost" if env_host in LOCAL_HOSTS else "remote"
    args = [_npx(), "hardhat", "run", "scripts/deploy.ts"]
    if network == "localhost":
        args += ["--network", "localhost"]
    proc = subprocess.run(args, cwd=blockchain_dir, capture_output=True, text=True, timeout=600)
    address = _read_shared_config()
    if proc.returncode != 0 or not address:
        tail = (proc.stdout + proc.stderr)[-500:]
        raise ChainError(f"Contract deployment failed: {tail}")
    return address


def get_w3_and_contract() -> tuple[Any, Any]:
    """Return a cached (web3 client, contract) pair, starting and deploying
    the local chain automatically when possible."""
    from web3 import Web3

    key = f"{settings.chain_rpc_url}"
    with _lock:
        cached = _cache.get(key)
        if cached and cached[0].is_connected():
            return cached

        host = settings.chain_rpc_url.split("//")[-1].split(":")[0]
        w3 = None
        try:
            w3 = Web3(Web3.HTTPProvider(settings.chain_rpc_url, request_kwargs={"timeout": 5}))
        except Exception as exc:
            raise ChainError(f"Cannot create chain client: {exc}") from exc

        if not w3.is_connected():
            is_local = host in LOCAL_HOSTS
            if not is_local:
                raise ChainError(f"Chain unreachable at {settings.chain_rpc_url}")
            # Auto-start the local Hardhat node.
            if not _node_modules_ready():
                raise ChainError(
                    "blockchain/node_modules missing; run ./make install:blockchain first."
                )
            blockchain_dir = _repo_root() / "blockchain"
            _spawn_detached(
                [_npx(), "hardhat", "node"], blockchain_dir, blockchain_dir / "hardhat-node.log"
            )
            w3 = _wait_for_rpc(settings.chain_rpc_url, lambda u: Web3(Web3.HTTPProvider(u)))
            if w3 is None:
                raise ChainError(
                    "Local Hardhat node did not start; see blockchain/hardhat-node.log"
                )

        address = settings.contract_address or _read_shared_config()
        if not address:
            address = _deploy()
        contract = w3.eth.contract(address=Web3.to_checksum_address(address), abi=_load_abi())
        _cache[key] = (w3, contract)
        return w3, contract


def _issuer_account():
    from eth_account import Account

    if not settings.demo_issuer_private_key:
        raise ChainError("DEMO_ISSUER_PRIVATE_KEY is not configured")
    return Account.from_key(settings.demo_issuer_private_key)


def _send(contract_call) -> dict[str, Any]:
    """Sign, send and wait for one contract transaction from the demo issuer."""
    w3 = get_w3_and_contract()[0]
    account = _issuer_account()
    tx = contract_call.build_transaction(
        {
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address),
            "gas": 700_000,
            "gasPrice": w3.eth.gas_price or 1_000_000_000,
            "chainId": w3.eth.chain_id,
        }
    )
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    if receipt.status != 1:
        raise ChainError(f"Transaction reverted: {tx_hash.hex()}")
    return {"tx_hash": tx_hash.hex(), "block_number": receipt.blockNumber}


def new_credential_id32() -> bytes:
    """Fresh unique bytes32 credential id (keccak of a uuid)."""
    from web3 import Web3

    return Web3.keccak(text=str(uuid.uuid4()))


def issue_onchain(doc_hash: str, recipient: str) -> dict[str, Any]:
    """Anchor doc_hash (0x-hex bytes32) for the recipient. Returns
    {chain_credential_id, doc_hash, tx_hash, block_number, issuer, recipient}."""
    from web3 import Web3

    _, contract = get_w3_and_contract()
    credential_id = new_credential_id32()
    recipient_cs = Web3.to_checksum_address(recipient)
    call = contract.functions.issueCredential(credential_id, Web3.to_hex(bytes.fromhex(doc_hash[2:])), recipient_cs)
    sent = _send(call)
    account = _issuer_account()
    return {
        "chain_credential_id": Web3.to_hex(credential_id),
        "doc_hash": doc_hash.lower(),
        "tx_hash": sent["tx_hash"],
        "block_number": sent["block_number"],
        "issuer_address": account.address,
        "recipient_address": recipient_cs,
    }


# Status codes mirror the contract enum: 0 Unknown, 1 Valid, 2 Tampered, 3 Revoked
STATUS_UNKNOWN, STATUS_VALID, STATUS_TAMPERED, STATUS_REVOKED = 0, 1, 2, 3


def verify_onchain(chain_credential_id: str, presented_doc_hash: str) -> int:
    """Compare a presented 64-hex digest with the anchored record on-chain.
    Accepts the hash with or without the 0x prefix."""

    _, contract = get_w3_and_contract()
    id_bytes = bytes.fromhex(chain_credential_id[2:])
    bare = presented_doc_hash.strip().lower().removeprefix("0x")
    hash_bytes = bytes.fromhex(bare)
    return int(contract.functions.verifyCredential(id_bytes, hash_bytes).call())


def get_onchain_credential(chain_credential_id: str) -> dict[str, Any]:
    from web3 import Web3

    _, contract = get_w3_and_contract()
    record = contract.functions.getCredential(bytes.fromhex(chain_credential_id[2:])).call()
    (doc_hash, issuer, recipient, issued_at, revoked_at, revoke_reason, revoked, exists) = record
    return {
        "doc_hash": Web3.to_hex(doc_hash).lower(),
        "issuer": issuer,
        "recipient": recipient,
        "issued_at": int(issued_at),
        "revoked_at": int(revoked_at),
        "revoke_reason": revoke_reason,
        "revoked": bool(revoked),
        "exists": bool(exists),
    }


def revoke_onchain(chain_credential_id: str, reason: str) -> dict[str, Any]:
    _, contract = get_w3_and_contract()
    call = contract.functions.revokeCredential(bytes.fromhex(chain_credential_id[2:]), reason)
    sent = _send(call)
    return {"tx_hash": sent["tx_hash"], "block_number": sent["block_number"]}
