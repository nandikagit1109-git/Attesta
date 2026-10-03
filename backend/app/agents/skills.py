"""Skill Graph Agent.

Maps extracted evidence skills to the standard taxonomy (data/skills.json)
and produces graph edges from evidence to skills with a strength value.
Deterministic: names match by exact name (strength 1.0) or alias (0.85).
"""

from .base import AgentContext, AgentResult, BaseAgent
from .evidence import load_taxonomy


class SkillGraphAgent(BaseAgent):
    name = "skill-graph"

    def run(self, ctx: AgentContext) -> AgentResult:
        evidence_id = ctx.evidence.id if ctx.evidence else "none"
        extracted = (ctx.evidence.extracted if ctx.evidence else {}) or {}
        raw_skills = extracted.get("skills", [])
        input_summary = f"map {len(raw_skills)} extracted skills to taxonomy (evidence {evidence_id})"

        taxonomy = load_taxonomy()
        by_id = {s["id"]: s for s in taxonomy.values()}

        skills = []
        edges = []
        for raw in raw_skills:
            skill_id = raw.get("id") or ""
            strength = float(raw.get("confidence") or 0.5)
            skill = by_id.get(skill_id)
            if skill is None and raw.get("name"):
                skill = taxonomy.get(str(raw["name"]).strip().lower())
            if skill is None:
                continue
            if all(s["id"] != skill["id"] for s in skills):
                skills.append({
                    "id": skill["id"],
                    "name": skill["name"],
                    "category": skill["category"],
                    "confidence": round(strength, 2),
                })
                edges.append({"from": evidence_id, "to": skill["id"], "strength": round(strength, 2)})

        flags = ["no-skills-mapped"] if not skills else []
        confidence = 0.9 if skills else 0.3
        return AgentResult(
            input_summary=input_summary,
            output={"skills": skills, "edges": edges},
            confidence=confidence,
            flags=flags,
            used_fallback=True,  # deterministic by design
        )
