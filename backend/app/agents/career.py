"""Career Mentor Agent.

Compares a student's verified and unverified skills to a target role from
data/roles.json. Verified skills count above unverified ones. Output: match
score, matched skills, missing skills with priorities, three project ideas
and a reasoning string. Deterministic by design so the demo never breaks.
"""

import json
from pathlib import Path

from ..config import get_settings
from .base import AgentContext, AgentResult, BaseAgent

# Priority labels: top third of weights are high, middle medium, rest low.
PROJECT_IDEAS = {
    "sql": "Build a small analytics database: model the schema, load a public "
    "dataset and answer ten business questions with SQL only.",
    "python": "Write a Python script that cleans a messy public dataset and "
    "produces a tidy summary report end to end.",
    "data-visualization": "Publish a dashboard that tells one clear story from a "
    "public dataset, with charts chosen for the message.",
    "excel": "Reproduce a business report in Excel with pivot tables and clear "
    "documentation of the steps.",
    "statistics": "Run an A/B style analysis on a public dataset: state the "
    "hypothesis, test it and explain the result plainly.",
    "communication": "Present one of your analyses as a five-slide story for a "
    "non-technical audience.",
    "power-bi": "Recreate one of your dashboards in Power BI and compare the "
    "strengths of each tool.",
    "javascript": "Build a small interactive web app that consumes a public API, "
    "with clean components and error states.",
    "react": "Build a React app with client-side routing and state that solves "
    "one real problem well.",
    "html-css": "Rebuild a well-known page layout from scratch with responsive, "
    "accessible HTML/CSS.",
    "typescript": "Convert a small JavaScript project to TypeScript and document "
    "the type design decisions.",
    "rest-api": "Design and ship a small REST API with validation, error handling "
    "and documentation.",
    "git": "Collaborate on any project using branch-per-feature workflow with "
    "clear commit history.",
    "testing": "Add a test suite to one of your existing projects and report the "
    "coverage improvement.",
    "accessibility": "Audit one of your projects against WCAG basics and fix the "
    "findings.",
    "machine-learning": "Train and evaluate a model on a tabular dataset, "
    "documenting feature choices and metrics honestly.",
    "deep-learning": "Fine-tune a small pretrained model on a niche dataset and "
    "write up the results.",
    "pandas": "Perform a full EDA on a fresh dataset with pandas and publish the "
    "notebook.",
    "docker": "Containerize one of your projects with a working compose file and "
    "README.",
    "etl": "Build a small ETL pipeline that moves data from a raw source to a "
    "queryable table on a schedule.",
    "solidity": "Write, test and deploy a small smart contract with a full Hardhat "
    "test suite.",
    "smart-contracts": "Implement an ERC-style token contract with tests for every access-control rule.",
    "ethereum": "Build a dapp that reads and writes on-chain state through a clean frontend.",
    "web3": "Integrate wallet signing into a project and document the security considerations.",
    "hardhat": "Set up contract tests that prove both the happy path and the unauthorized paths.",
    "cryptography": "Implement a hash-commitment demo and explain exactly what it does and does not prove.",
}


def load_roles() -> dict:

    settings = get_settings()
    path = Path(settings.resolve("../data/roles.json"))
    return json.loads(path.read_text(encoding="utf-8"))


def get_role(role_id: str | None) -> dict:
    data = load_roles()
    roles = data["roles"]
    if role_id:
        for role in roles:
            if role["id"] == role_id:
                return role
    default = data.get("default_target_role_id")
    for role in roles:
        if role["id"] == default:
            return role
    return roles[0]


def priority_for(weight: float, max_weight: float) -> str:
    if weight >= max_weight * 0.8:
        return "High"
    if weight >= max_weight * 0.5:
        return "Medium"
    return "Low"


def score_skills(
    required: list[dict], verified: set[str], unverified: set[str]
) -> tuple[float, list[dict], list[dict], list[dict]]:
    """Weighted coverage. Verified counts fully, unverified at 0.4.

    Returns (score 0..100, matched, missing, unverified_list)."""
    max_weight = max((r["weight"] for r in required), default=1.0)
    total = sum(r["weight"] for r in required) or 1.0
    earned = 0.0
    matched, missing, unverified_list = [], [], []

    for req in required:
        sid, weight = req["skill_id"], req["weight"]
        if sid in verified:
            earned += weight
            matched.append({"skill_id": sid, "weight": weight, "verified": True})
        elif sid in unverified:
            earned += weight * 0.4
            unverified_list.append({"skill_id": sid, "weight": weight})
        else:
            missing.append(
                {"skill_id": sid, "weight": weight, "priority": priority_for(weight, max_weight)}
            )

    missing.sort(key=lambda m: -m["weight"])
    return round(earned / total * 100), matched, missing, unverified_list


class CareerMentorAgent(BaseAgent):
    name = "career-mentor"

    def run(self, ctx: AgentContext) -> AgentResult:
        verified = set(ctx.params.get("verified_skills", []))
        unverified = set(ctx.params.get("unverified_skills", []))
        role = get_role(ctx.params.get("role_id"))
        job_mode = bool(ctx.params.get("job_mode"))

        input_summary = (
            f"score {len(verified)} verified / {len(unverified)} unverified skills "
            f"against role '{role['id']}'" + (" for a job description" if job_mode else "")
        )

        score, matched, missing, unverified_list = score_skills(
            role["required_skills"], verified, unverified
        )
        ideas = self._project_ideas(missing)
        reasoning = self._reasoning(role, score, matched, missing, verified, unverified, job_mode)

        return AgentResult(
            input_summary=input_summary,
            output={
                "role": {"id": role["id"], "title": role["title"]},
                "score": score,
                "matched": matched,
                "missing": missing,
                "unverified": unverified_list,
                "project_ideas": ideas,
                "reasoning": reasoning,
            },
            confidence=0.85 if verified else 0.5,
            flags=[] if verified else ["no-verified-skills"],
            used_fallback=True,  # deterministic by design
        )

    @staticmethod
    def _project_ideas(missing: list[dict]) -> list[str]:
        ideas: list[str] = []
        for m in missing:
            idea = PROJECT_IDEAS.get(m["skill_id"])
            if idea and idea not in ideas:
                ideas.append(idea)
            if len(ideas) == 3:
                break
        while len(ideas) < 3:
            ideas.append(
                "Pick one missing skill and ship the smallest real project that uses it end to end."
            )
        return ideas

    @staticmethod
    def _reasoning(role, score, matched, missing, verified, unverified, job_mode) -> str:
        parts = []
        verified_matched = ", ".join(m["skill_id"] for m in matched) or "none yet"
        parts.append(
            f"Score {score}/100 against {role['title']}: verified skills counted in full "
            f"({verified_matched}); unverified skills counted at 40 percent."
        )
        if missing:
            top = ", ".join(m["skill_id"] for m in missing[:3])
            parts.append(f"Highest-priority gaps: {top}.")
        if not verified and unverified:
            parts.append(
                "Nothing is verified yet: get any certificate or project approved by an "
                "issuer to move these skills into the verified set."
            )
        if job_mode:
            parts.append(
                "Job match uses issuer-verified skills only for the score; unverified "
                "matches are listed separately and never inflate the score."
            )
        return " ".join(parts)
