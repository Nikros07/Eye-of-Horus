"""Pluggable LLM backend for the research layer.

Without a configured provider key, `get_llm_provider()` returns None and
callers fall back to the deterministic synthesizer — the system must work,
and must never fabricate evidence, either way. With a key, the configured
provider is used, but it is still given only the structured EvidenceBundle
and an explicit instruction to answer INSUFFICIENT EVIDENCE rather than
invent facts.

LLM_PROVIDER selects which one: "anthropic" (default, needs
ANTHROPIC_API_KEY) or "gemini" (needs GEMINI_API_KEY — Google AI Studio
issues a free-tier key with no card required). Both implement the same
LLMProvider interface, so synthesizer.py never knows which is active.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod

from app.core.config import get_settings

SYSTEM_PROMPT = """You are the research layer of an event-to-market intelligence platform.
You are given ONLY a structured JSON evidence bundle about one real-world event and the
mechanical signals a rules-based strategy engine already generated from it.

Rules you must follow exactly:
- Never state anything as fact unless it is present in the evidence bundle.
- Classify every statement you make under one of: OBSERVED, DERIVED, HYPOTHESIS, UNCERTAIN.
- If the evidence bundle does not contain enough to answer a section, write "INSUFFICIENT EVIDENCE" for that section instead of guessing.
- You do not decide whether to trade. The strategy engine already decided that from fixed rules; you only explain and critique.
- Answer strictly as JSON with keys: observed (list[str]), derived (list[str]), hypothesis (list[str]),
  uncertain (list[str]), risks (list[str]), invalidation (list[str]), market_already_priced ("NO"|"POSSIBLY"|"YES"),
  historical_analogues (str).
"""


class LLMProvider(ABC):
    # One of "claude" / "gemini" — ResearchOutput.source is set to this on
    # a successful synthesis, so the frontend can show which model answered.
    source_label: str

    @abstractmethod
    def synthesize(self, evidence_bundle: dict) -> dict | None: ...


class ClaudeProvider(LLMProvider):
    source_label = "claude"

    def __init__(self, api_key: str) -> None:
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)

    def synthesize(self, evidence_bundle: dict) -> dict | None:
        message = self._client.messages.create(
            model="claude-sonnet-5",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": json.dumps(evidence_bundle)}],
        )
        text = "".join(block.text for block in message.content if hasattr(block, "text"))
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None


class GeminiProvider(LLMProvider):
    """Calls Google's Gemini API directly over REST (no extra SDK
    dependency — same approach as the NASA EONET/Open-Meteo connectors),
    asking for a JSON response via `responseMimeType` so the same parsing
    path as ClaudeProvider works unchanged.
    """

    source_label = "gemini"

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    def synthesize(self, evidence_bundle: dict) -> dict | None:
        import httpx

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent"
        body = {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": json.dumps(evidence_bundle)}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        try:
            with httpx.Client(timeout=20.0) as client:
                resp = client.post(url, params={"key": self._api_key}, json=body)
                resp.raise_for_status()
                payload = resp.json()
        except httpx.HTTPError:
            return None

        try:
            text = payload["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text)
        except (KeyError, IndexError, json.JSONDecodeError):
            return None


def get_llm_provider() -> LLMProvider | None:
    settings = get_settings()
    try:
        if settings.llm_provider == "gemini":
            if not settings.gemini_api_key:
                return None
            return GeminiProvider(settings.gemini_api_key, settings.gemini_model)
        if not settings.anthropic_api_key:
            return None
        return ClaudeProvider(settings.anthropic_api_key)
    except Exception:  # noqa: BLE001
        return None
