"""Profile Agent. Produces a short summary using ONLY facts present in the
profile, evidence and credentials. Deterministic; it never invents anything.
"""

from .base import AgentContext, AgentResult, BaseAgent


class ProfileAgent(BaseAgent):
    name = "profile"

    def run(self, ctx: AgentContext) -> AgentResult:
        user = ctx.params["user"]
        facts: dict = ctx.params["facts"]  # {verified_skills, unverified_skills, projects, credentials}
        input_summary = f"summarize profile facts for {user.email}"

        name = user.full_name
        role_label = user.role if user.role != "issuer" else f"issuer ({user.org_name})" if user.org_name else "issuer"

        parts = [f"{name} is a {role_label}."]

        verified = facts.get("verified_skills", [])
        if verified:
            parts.append(f"Verified skills: {', '.join(verified[:8])}.")
        unverified = facts.get("unverified_skills", [])
        if unverified:
            parts.append(
                f"Also reports {', '.join(unverified[:6])} (Unverified, not yet issuer-confirmed)."
            )
        creds = facts.get("credentials", [])
        if creds:
            parts.append(f"Verified credentials on-chain: {len(creds)}.")
        projects = facts.get("projects", [])
        if projects:
            titles = ", ".join(p["title"] for p in projects[:3])
            parts.append(f"Projects: {titles}.")
        if user.headline:
            parts.append(user.headline)

        summary = " ".join(parts)
        return AgentResult(
            input_summary=input_summary,
            output={"summary": summary, "fact_count": sum(
                [len(verified), len(unverified), len(creds), len(projects)]
            )},
            confidence=1.0,
            flags=[] if (verified or creds) else ["profile-empty"],
            used_fallback=True,
        )
