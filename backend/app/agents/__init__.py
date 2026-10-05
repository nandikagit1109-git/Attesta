"""Attesta agent layer: orchestrator plus five agents.

Every agent returns an AgentResult; the orchestrator persists one AgentRun row
per execution (Agent Trace panel) plus an AGENT_RUN audit entry. The
Integrity Agent is the only one allowed to change trust to
Verified / Revoked / Tampered, and it is pure deterministic code.
"""
