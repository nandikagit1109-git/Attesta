"""Database models. wallet_private_key exists ONLY for the wallet-less demo
flow (backend-generated student addresses, demo key signing on the local
chain). It is never returned by any API response."""

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # student|issuer|recruiter
    org_name: Mapped[str] = mapped_column(String(255), default="")
    headline: Mapped[str] = mapped_column(String(500), default="")
    # Per-field privacy toggles for the public profile (feature 9).
    public_fields: Mapped[dict] = mapped_column(JSON, default=dict)
    wallet_address: Mapped[str] = mapped_column(String(42), default="")
    wallet_private_key: Mapped[str] = mapped_column(String(66), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    evidences: Mapped[list["Evidence"]] = relationship(back_populates="student")
    projects: Mapped[list["Project"]] = relationship(back_populates="student")


class Evidence(Base):
    """An uploaded document plus what the AI extracted from it."""

    __tablename__ = "evidences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(300), default="")
    file_name: Mapped[str] = mapped_column(String(300), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False)
    # Demo-only copy with one flipped byte, for the tamper demonstration.
    tampered_copy_path: Mapped[str] = mapped_column(String(500), default="")
    mime_type: Mapped[str] = mapped_column(String(100), default="")
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    sha256: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    # Agent extraction: {title, issuer, student_name, date, credential_id, skills:[{id,name,confidence}], text_chars}
    extracted: Mapped[dict] = mapped_column(JSON, default=dict)
    # One of TrustState values. Starts AI_EXTRACTED; only the Integrity Agent
    # ever moves it to ISSUER_VERIFIED / REVOKED / TAMPERED.
    trust_state: Mapped[str] = mapped_column(String(40), index=True, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    student: Mapped[User] = relationship(back_populates="evidences")
    credential: Mapped["Credential | None"] = relationship(back_populates="evidence", uselist=False)
    agent_runs: Mapped[list["AgentRun"]] = relationship(back_populates="evidence")


class Credential(Base):
    """On-chain anchor of one evidence document (mirrored off-chain for UX)."""

    __tablename__ = "credentials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # bytes32 id on-chain, stored as 0x-hex
    chain_credential_id: Mapped[str] = mapped_column(String(66), unique=True, index=True, nullable=False)
    evidence_id: Mapped[str] = mapped_column(ForeignKey("evidences.id"), unique=True, nullable=False)
    issuer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    recipient_address: Mapped[str] = mapped_column(String(42), nullable=False)
    doc_hash: Mapped[str] = mapped_column(String(66), nullable=False, index=True)
    tx_hash: Mapped[str] = mapped_column(String(66), default="")
    block_number: Mapped[int] = mapped_column(Integer, default=0)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoke_reason: Mapped[str] = mapped_column(String(300), default="")
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    evidence: Mapped[Evidence] = relationship(back_populates="credential")
    issuer: Mapped[User] = relationship()


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    skills: Mapped[list] = mapped_column(JSON, default=list)  # list of skill ids
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    student: Mapped[User] = relationship(back_populates="projects")


class AgentRun(Base):
    """One row per agent execution; powers the Agent Trace panel."""

    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # Nullable: career/profile/job-match runs are not tied to one evidence.
    evidence_id: Mapped[str | None] = mapped_column(
        ForeignKey("evidences.id"), index=True, nullable=True
    )
    agent: Mapped[str] = mapped_column(String(40), nullable=False)
    input_summary: Mapped[str] = mapped_column(Text, default="")
    output: Mapped[dict] = mapped_column(JSON, default=dict)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    flags: Mapped[list] = mapped_column(JSON, default=list)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    used_fallback: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    evidence: Mapped[Evidence] = relationship(back_populates="agent_runs")


class AuditLog(Base):
    """Audit trail of every issue, revoke, verify and agent run."""

    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    actor_id: Mapped[str] = mapped_column(String(36), default="")
    actor_role: Mapped[str] = mapped_column(String(20), default="")
    action: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    object_type: Mapped[str] = mapped_column(String(40), default="")
    object_id: Mapped[str] = mapped_column(String(80), default="")
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
