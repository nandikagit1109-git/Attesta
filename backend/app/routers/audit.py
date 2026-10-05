"""Public, read-only audit log (feature 6).

Anyone can read it, no login. It shows exactly what the chain proves and
nothing else: registry events (issued, revoked) read from the contract's
event logs — or from the server's mirror of them when the node is
unreachable — plus off-chain tamper-detection entries labeled "off-chain".

Rows carry only hashes, addresses, event types, transaction hashes and
timestamps. No names, no emails, no file names, and no way to enumerate
profiles or download files.
"""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import chain
from ..db import get_db
from ..models import AuditLog, Credential

router = APIRouter(prefix="/api/audit", tags=["audit"])


def _iso(epoch_seconds: int | None) -> str | None:
    if not epoch_seconds:
        return None
    return datetime.fromtimestamp(int(epoch_seconds), tz=UTC).isoformat()


def _chain_event_rows() -> list[dict[str, Any]] | None:
    """Read the registry's own event logs. Returns None when the chain is
    unreachable so the caller falls back to its mirror of the same facts."""
    if not chain.is_reachable():
        return None
    try:
        _, contract = chain.get_w3_and_contract()
        issued_logs = contract.events.CredentialIssued.get_logs(from_block=0)
        revoked_logs = contract.events.CredentialRevoked.get_logs(from_block=0)
    except Exception:
        return None

    from web3 import Web3

    rows: list[dict[str, Any]] = []
    for log in issued_logs:
        args = log["args"]
        rows.append(
            {
                "event": "issued",
                "source": "chain",
                "credential_id": Web3.to_hex(args["credentialId"]),
                "doc_hash": Web3.to_hex(args["docHash"]),
                "issuer_address": args["issuer"],
                "tx_hash": log["transactionHash"].to_0x_hex(),
                "block_number": log["blockNumber"],
                "at": _iso(args["issuedAt"]),
                "reason": "",
            }
        )
    for log in revoked_logs:
        args = log["args"]
        rows.append(
            {
                "event": "revoked",
                "source": "chain",
                "credential_id": Web3.to_hex(args["credentialId"]),
                "doc_hash": None,
                "issuer_address": args["revokedBy"],
                "tx_hash": log["transactionHash"].to_0x_hex(),
                "block_number": log["blockNumber"],
                "at": _iso(args["revokedAt"]),
                "reason": args["reason"],
            }
        )
    return rows


def _mirror_rows(db: Session) -> list[dict[str, Any]]:
    """Fallback when the node is down: the same chain facts from the local
    mirror rows written at issue/revoke time."""
    rows: list[dict[str, Any]] = []
    for c in db.query(Credential).order_by(Credential.issued_at).all():
        rows.append(
            {
                "event": "issued",
                "source": "chain",
                "credential_id": c.chain_credential_id,
                "doc_hash": f"0x{c.doc_hash}",
                "issuer_address": c.issuer_address,
                "tx_hash": c.tx_hash,
                "block_number": c.block_number,
                "at": c.issued_at.isoformat() if c.issued_at else None,
                "reason": "",
            }
        )
        if c.revoked:
            rows.append(
                {
                    "event": "revoked",
                    "source": "chain",
                    "credential_id": c.chain_credential_id,
                    "doc_hash": f"0x{c.doc_hash}",
                    "issuer_address": c.issuer_address,
                    "tx_hash": c.tx_hash,
                    "block_number": c.block_number,
                    "at": c.revoked_at.isoformat() if c.revoked_at else None,
                    "reason": c.revoke_reason,
                }
            )
    return rows


def _offchain_rows(db: Session) -> list[dict[str, Any]]:
    """Tamper-detection entries. These never touch the chain (the registry is
    immutable), so they are labeled off-chain."""
    credential_addresses = {
        c.id: c.issuer_address for c in db.query(Credential).all()
    }
    rows: list[dict[str, Any]] = []
    tamper_rows = (
        db.query(AuditLog)
        .filter(AuditLog.action == "TAMPER")
        .order_by(AuditLog.created_at)
        .all()
    )
    for row in tamper_rows:
        detail = row.detail or {}
        rows.append(
            {
                "event": "tamper-detected",
                "source": "off-chain",
                "credential_id": row.object_id or None,
                "doc_hash": detail.get("tampered_sha256"),
                "issuer_address": credential_addresses.get(row.object_id, ""),
                "tx_hash": None,
                "block_number": None,
                "at": row.created_at.isoformat() if row.created_at else None,
                "reason": detail.get("original_sha256"),
            }
        )
    return rows


@router.get("")
def public_audit(
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Public feed: chain events (or their mirror) + off-chain tamper entries,
    newest first. Deliberately excludes LOGIN/UPLOAD/AGENT_RUN/VERIFY rows and
    every actor identity."""
    events = _chain_event_rows()
    if events is None:
        events = _mirror_rows(db)
    events.extend(_offchain_rows(db))

    events.sort(key=lambda r: r.get("at") or "", reverse=True)
    for row in events:
        row["key"] = f"{row['event']}:{row.get('credential_id') or ''}:{row.get('tx_hash') or ''}"
    return events[:limit]
