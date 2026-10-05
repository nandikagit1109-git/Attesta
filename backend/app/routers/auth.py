"""Auth endpoints: register, login, me, and one-click demo logins."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import AuditLog, User
from ..schemas import DEFAULT_PUBLIC_FIELDS, LoginRequest, RegisterRequest, user_public
from ..security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Demo accounts (feature 5): one click each, no passwords typed on stage.
# Recruiters are guests — they never log in; they open a share link.
DEMO_USERS = {
    "student": {
        "email": "student@attesta.demo",
        "full_name": "Ananya Sharma",
        "org_name": "",
        "headline": "Aspiring Data Analyst. Sample data profile for the Attesta demo.",
    },
    "issuer": {
        "email": "issuer@attesta.demo",
        "full_name": "Registrar Office",
        "org_name": "Springfield College",
        "headline": "Issues and verifies student credentials. Sample data issuer.",
    },
    "admin": {
        "email": "admin@attesta.demo",
        "full_name": "Demo Admin",
        "org_name": "Attesta",
        "headline": "Owns the demo dataset, reset and the one-click tamper.",
    },
}
DEMO_PASSWORD = "attesta-demo"


def _audit_login(db: Session, user: User) -> None:
    db.add(
        AuditLog(
            id=str(uuid.uuid4()),
            actor_id=user.id,
            actor_role=user.role,
            action="LOGIN",
            object_type="user",
            object_id=user.id,
            detail={"mode": "demo" if user.email.endswith("@attesta.demo") else "password"},
        )
    )
    db.commit()


@router.post("/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    from ..security import generate_wallet

    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    wallet_address, wallet_key = ("", "")
    if payload.role == "student":
        # Students never need MetaMask: the backend generates their address.
        wallet_address, wallet_key = generate_wallet()

    user = User(
        id=str(uuid.uuid4()),
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        role=payload.role,
        org_name=payload.org_name.strip(),
        public_fields=dict(DEFAULT_PUBLIC_FIELDS),
        wallet_address=wallet_address,
        wallet_private_key=wallet_key,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"token": create_access_token(user), "user": user_public(user)}


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    _audit_login(db, user)
    return {"token": create_access_token(user), "user": user_public(user)}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return user_public(user)


@router.post("/demo/{role}")
def demo_login(role: str, db: Session = Depends(get_db)):
    """One-click login for the demo (feature 5). Creates the demo user on
    first use so the demo works on a fresh database."""
    if role not in DEMO_USERS:
        raise HTTPException(
            status_code=404,
            detail="Demo role must be student, issuer or admin; recruiters are guests",
        )

    spec = DEMO_USERS[role]
    user = db.query(User).filter(User.email == spec["email"]).first()
    if user is None:
        wallet_address, wallet_key = ("", "")
        if role == "student":
            from ..security import generate_wallet

            wallet_address, wallet_key = generate_wallet()
        user = User(
            id=str(uuid.uuid4()),
            email=spec["email"],
            password_hash=hash_password(DEMO_PASSWORD),
            full_name=spec["full_name"],
            role=role,
            org_name=spec["org_name"],
            headline=spec["headline"],
            public_fields=dict(DEFAULT_PUBLIC_FIELDS),
            wallet_address=wallet_address,
            wallet_private_key=wallet_key,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    _audit_login(db, user)
    return {"token": create_access_token(user), "user": user_public(user)}
