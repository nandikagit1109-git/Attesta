"""Agent framework: shared context, result type, run recording.

Every agent returns an AgentResult; the orchestrator persists one AgentRun row
per execution (Agent Trace panel) plus an AGENT_RUN audit entry.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from ..models import AgentRun, AuditLog, Evidence, User


@dataclass
class AgentContext:
    db: Session
    evidence: Evidence | None = None
    actor: User | None = None
    params: dict[str, Any] = field(default_factory=dict)


class AgentResult:
    def __init__(
        self,
        input_summary: str,
        output: dict[str, Any],
        confidence: float,
        flags: list[str] | None = None,
        used_fallback: bool = False,
    ):
        self.input_summary = input_summary
        self.output = output
        self.confidence = max(0.0, min(1.0, confidence))
        self.flags = flags or []
        self.used_fallback = used_fallback


class BaseAgent:
    """Subclasses set `name` and implement run(). run() must never raise for
    expected data problems; problems surface as flags on the result."""

    name: str = "agent"

    def run(self, ctx: AgentContext) -> AgentResult:  # pragma: no cover - interface
        raise NotImplementedError

    def execute(self, ctx: AgentContext) -> tuple[AgentRun, AgentResult]:
        """Run the agent, persist the AgentRun row and the audit entry, and
        return both. Called only via the orchestrator."""
        started = time.perf_counter()
        try:
            result = self.run(ctx)
        except Exception as exc:  # a broken agent must never kill a request
            result = AgentResult(
                input_summary=f"{self.name} crashed: {type(exc).__name__}",
                output={"error": str(exc)},
                confidence=0.0,
                flags=["agent-error"],
                used_fallback=True,
            )
        duration_ms = int((time.perf_counter() - started) * 1000)

        run_row = AgentRun(
            id=str(uuid.uuid4()),
            evidence_id=ctx.evidence.id if ctx.evidence is not None else None,
            agent=self.name,
            input_summary=result.input_summary[:2000],
            output=result.output,
            confidence=result.confidence,
            flags=result.flags,
            duration_ms=duration_ms,
            used_fallback=result.used_fallback,
        )
        ctx.db.add(run_row)
        ctx.db.add(
            AuditLog(
                id=str(uuid.uuid4()),
                actor_id=ctx.actor.id if ctx.actor else "",
                actor_role=ctx.actor.role if ctx.actor else "",
                action="AGENT_RUN",
                object_type="evidence" if ctx.evidence is not None else "session",
                object_id=ctx.evidence.id if ctx.evidence is not None else "",
                detail={"agent": self.name, "confidence": result.confidence, "flags": result.flags},
            )
        )
        ctx.db.flush()
        return run_row, result
