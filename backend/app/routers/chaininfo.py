"""Public chain coordinates for the frontend's direct on-chain reads.

The verify page and receipts re-read the registry contract with ethers v6
straight from the browser, so anyone can check a credential without trusting
Attesta's servers. This endpoint hands out only public configuration:
RPC URL, chain id and the deployed registry address.
"""

from fastapi import APIRouter

from .. import chain
from ..config import get_settings

router = APIRouter(prefix="/api/chain", tags=["chain"])


@router.get("")
def chain_info():
    settings = get_settings()
    address = chain.contract_address()
    return {
        "chain_id": settings.chain_id,
        "rpc_url": settings.chain_rpc_url,
        "contract_address": address,
        "deployed": bool(address),
        "explorer_url": "",
    }
