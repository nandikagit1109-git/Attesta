"""Evidence Verification Agent.

Extracts title, issuer, student name, date, credential id and skills from a
document, and flags missing or suspicious fields. It NEVER claims a document
is authentic: authenticity comes only from the issuer + chain (Integrity
Agent). Uses the LLM when configured, otherwise a deterministic
keyword-and-regex extractor that works well on the seeded certificates.
"""

import re
from pathlib import Path

from ..config import get_settings
from .base import AgentContext, AgentResult, BaseAgent
from .llm import chat_json, llm_available

JSON_HINT = '{"title": str, "issuer": str, "student_name": str, "date": str, "credential_id": str, "skills": [str]}'

FIELD_KEYS = ["title", "issuer", "student_name", "date", "credential_id"]

ISSUER_RE = re.compile(
    r"(university|college|institute|academy|school|registrar|department of|"
    r"awarded by|issued by|certified by)", re.IGNORECASE
)
NAME_RE = re.compile(
    r"(?:this is to certify that|awarded to|presented to|certifies that|"
    r"successfully completed by)\s+([A-Z][A-Za-z .'-]{2,60})",
    re.IGNORECASE,
)
DATE_RES = [
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
    re.compile(
        r"\b\d{1,2}[ -/.](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[ -/.]\d{2,4}\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.? \d{1,2},? \d{4}\b", re.IGNORECASE),
    re.compile(r"\b\d{1,2}[ -/]\d{1,2}[ -/]\d{2,4}\b"),
]
CRED_ID_RE = re.compile(
    r"(?:credential id|certificate (?:no|number|id)|serial (?:no|number))\s*[:#-]?\s*([A-Za-z0-9][A-Za-z0-9-]{3,30})",
    re.IGNORECASE,
)


def load_taxonomy() -> dict:
    """{lowercase name or alias: {id, name, category}} from data/skills.json."""
    import json

    settings = get_settings()
    path = Path(settings.resolve("../data/skills.json"))
    data = json.loads(path.read_text(encoding="utf-8"))
    lookup: dict[str, dict] = {}
    for skill in data["skills"]:
        lookup[skill["name"].lower()] = skill
        for alias in skill.get("aliases", []):
            lookup[alias.lower()] = skill
    return lookup


class EvidenceAgent(BaseAgent):
    name = "evidence-verification"

    def run(self, ctx: AgentContext) -> AgentResult:
        text: str = ctx.params.get("text", "")
        file_name: str = ctx.params.get("file_name", "")
        truncated = text[:6000]
        input_summary = f"extract fields from '{file_name}' ({len(text)} chars of text)"

        if llm_available():
            parsed = chat_json(
                "You extract structured fields from certificate and project "
                "documents. Never claim a document is authentic; extraction is "
                "a suggestion only. Reply with JSON only.",
                f"Document text:\n{truncated}",
                JSON_HINT,
            )
            if parsed is not None:
                return self._from_llm(parsed, text, input_summary)
        return self._fallback(truncated, file_name, input_summary)

    def _from_llm(self, parsed: dict, text: str, input_summary: str) -> AgentResult:
        fields = {k: str(parsed.get(k) or "").strip() for k in FIELD_KEYS}
        taxonomy = load_taxonomy()
        skills = []
        for raw in parsed.get("skills") or []:
            match = taxonomy.get(str(raw).strip().lower())
            if match and match["id"] not in [s["id"] for s in skills]:
                skills.append({"id": match["id"], "name": match["name"], "confidence": 0.6})
        flags = self._missing_flags(fields)
        confidence = 0.75 if not flags else max(0.4, 0.75 - 0.1 * len(flags))
        return AgentResult(
            input_summary=input_summary,
            output={**fields, "skills": skills, "text_chars": len(text)},
            confidence=confidence,
            flags=flags,
            used_fallback=False,
        )

    def _fallback(self, text: str, file_name: str, input_summary: str) -> AgentResult:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

        title = next((ln for ln in lines if 4 <= len(ln) <= 120 and not ISSUER_RE.search(ln)), "")
        if not title and lines:
            title = lines[0]
        if not title:
            title = Path(file_name).stem.replace("-", " ").replace("_", " ")

        issuer = next((ln for ln in lines if ISSUER_RE.search(ln) and len(ln) <= 160), "")
        issuer = issuer if issuer else ""

        name = ""
        m = NAME_RE.search(text)
        if m:
            name = m.group(1).strip().rstrip(",.:")

        date = ""
        for rx in DATE_RES:
            m = rx.search(text)
            if m:
                date = m.group(0)
                break

        credential_id = ""
        m = CRED_ID_RE.search(text)
        if m:
            credential_id = m.group(1)

        # Skill mapping straight off the taxonomy (works offline, good on
        # the seeded certificates).
        taxonomy = load_taxonomy()
        lower_text = text.lower()
        skills = []
        for key, skill in taxonomy.items():
            is_known = key and re.search(rf"\b{re.escape(key)}\b", lower_text)
            if is_known and skill["id"] not in [s["id"] for s in skills]:
                conf = 0.85 if key == skill["name"].lower() else 0.7
                skills.append({"id": skill["id"], "name": skill["name"], "confidence": conf})
        skills = skills[:12]

        fields = {"title": title, "issuer": issuer, "student_name": name, "date": date, "credential_id": credential_id}
        flags = self._missing_flags(fields)
        found = sum(1 for k in FIELD_KEYS if fields[k])
        confidence = min(0.92, 0.35 + 0.12 * found + min(0.15, 0.03 * len(skills)))

        return AgentResult(
            input_summary=input_summary + " (deterministic fallback)",
            output={**fields, "skills": skills, "text_chars": len(text)},
            confidence=round(confidence, 2),
            flags=flags,
            used_fallback=True,
        )

    @staticmethod
    def _missing_flags(fields: dict) -> list[str]:
        import datetime

        flags = [f"missing:{k}" for k in FIELD_KEYS if not fields.get(k)]
        date = fields.get("date", "")
        if date:
            m = re.search(r"\b(\d{4})\b", date)
            if m and int(m.group(1)) > datetime.date.today().year + 1:
                flags.append("suspicious:date-in-future")
        return flags
