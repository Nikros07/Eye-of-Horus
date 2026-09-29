"""Pluggable LLM backend for the research layer.

Without an ANTHROPIC_API_KEY, `get_llm_provider()` returns None and callers
fall back to the deterministic synthesizer — the system must work, and must
never fabricate evidence, either way. With a key, ClaudeProvider is used,
but it is still given only the structured EvidenceBundle and an explicit
instruction to answer INSUFFICIENT EVIDENCE rather than invent facts.
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
    @abstractmethod
    def synthesize(self, evidence_bundle: dict) -> dict | None: ...


class ClaudeProvider(LLMProvider):
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


def get_llm_provider() -> LLMProvider | None:
    settings = get_settings()
    if not settings.anthropic_api_key:
        return None
    try:
        return ClaudeProvider(settings.anthropic_api_key)
    except Exception:  # noqa: BLE001
        return None
