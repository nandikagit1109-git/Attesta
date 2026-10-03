"""Auth: bcrypt password hashing, JWT bearer tokens, role-based access."""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db
from .models import User

settings = get_settings()
_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user: User) -> str:
    payload = {
        "sub": user.id,
        "role": user.role,
        "exp": datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes),
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    try:
        payload = decode_token(credentials.credentials)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from None
    user = db.get(User, payload.get("sub", ""))
    if user is None:
        raise HTTPException(status_code=401, detail="User no longer exists")
    return user


def require_roles(*roles: str) -> Callable:
    """Dependency factory: 403 unless the user has one of the given roles."""

    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"This action requires role: {' or '.join(roles)}",
            )
        return user

    return dependency


def generate_wallet() -> tuple[str, str]:
    """Backend-generated student address so students never need MetaMask.

    Returns (address, private_key). The key is stored demo-only; see
    models.User.wallet_private_key. On serverless (no web3 installed) wallet
    generation is skipped; chain features are unavailable there anyway.
    """
    try:
        from eth_account import Account
    except ImportError:  # serverless: chain extras not installed
        return "", ""

    acct = Account.create()
    return acct.address, acct.key.hex()


def new_id() -> str:
    return str(uuid.uuid4())
