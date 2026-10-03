"""Provider-agnostic LLM wrapper (OpenAI-compatible /chat/completions).

Contract with callers:
- Returns a parsed dict on success, or None on ANY failure (missing config,
  network error, non-JSON reply after one retry). Callers then run their
  deterministic fallback, so the whole product works offline with no key.
- Strict JSON: the first parse failure triggers exactly one retry that
  instructs the model to return only JSON.
"""

import json
import logging

import httpx

from ..config import get_settings

logger = logging.getLogger("attesta.llm")


def llm_available() -> bool:
    return get_settings().llm_configured


def chat_json(system: str, user: str, json_hint: str) -> dict | None:
    """One call, one strict-JSON retry, then give up and return None."""
    settings = get_settings()
    if not settings.llm_configured:
        return None

    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {settings.llm_api_key}"}
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    body = {
        "model": settings.llm_model,
        "messages": messages,
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    try:
        with httpx.Client(timeout=20.0) as client:
            parsed = _attempt(client, url, headers, body)
            if parsed is not None:
                return parsed
            # Exactly one retry, demanding JSON only.
            retry_messages = [
                *messages,
                {
                    "role": "user",
                    "content": f"Your previous reply was not valid JSON. "
                    f"Return ONLY a JSON object matching this shape, no prose: {json_hint}",
                },
            ]
            body["messages"] = retry_messages
            return _attempt(client, url, headers, body)
    except Exception as exc:
        logger.warning("LLM call failed, falling back: %s", exc)
        return None


def _attempt(client: httpx.Client, url: str, headers: dict, body: dict) -> dict | None:
    try:
        resp = client.post(url, json=body, headers=headers)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as exc:
        logger.info("LLM attempt unusable: %s", exc)
        return None
