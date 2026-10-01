from __future__ import annotations

from types import SimpleNamespace

import httpx

from app.services.research.llm_provider import GeminiProvider, get_llm_provider


def _mock_httpx_client(monkeypatch, handler) -> None:
    """Forces every httpx.Client created anywhere in the module under test
    to route through a MockTransport, regardless of how it was constructed —
    GeminiProvider builds its own client internally with no injection point.
    """
    original_init = httpx.Client.__init__

    def patched_init(self, *args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.Client, "__init__", patched_init)


def test_get_llm_provider_returns_none_without_any_key():
    assert get_llm_provider() is None


def test_get_llm_provider_returns_gemini_when_selected(monkeypatch):
    monkeypatch.setattr(
        "app.services.research.llm_provider.get_settings",
        lambda: SimpleNamespace(llm_provider="gemini", gemini_api_key="g-key", gemini_model="gemini-2.0-flash"),
    )
    provider = get_llm_provider()
    assert isinstance(provider, GeminiProvider)
    assert provider.source_label == "gemini"


def test_get_llm_provider_gemini_selected_but_no_key_returns_none(monkeypatch):
    monkeypatch.setattr(
        "app.services.research.llm_provider.get_settings",
        lambda: SimpleNamespace(llm_provider="gemini", gemini_api_key=None, gemini_model="gemini-2.0-flash"),
    )
    assert get_llm_provider() is None


def test_gemini_synthesize_parses_json_text_from_response(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith(":generateContent")
        assert request.url.params["key"] == "g-key"
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": '{"observed": ["x"], "market_already_priced": "NO"}'}]}}]},
        )

    _mock_httpx_client(monkeypatch, handler)
    provider = GeminiProvider(api_key="g-key", model="gemini-2.0-flash")
    result = provider.synthesize({"event_type": "flood"})

    assert result == {"observed": ["x"], "market_already_priced": "NO"}


def test_gemini_synthesize_returns_none_on_http_error(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "internal"})

    _mock_httpx_client(monkeypatch, handler)
    provider = GeminiProvider(api_key="g-key", model="gemini-2.0-flash")
    assert provider.synthesize({"event_type": "flood"}) is None


def test_gemini_synthesize_returns_none_on_malformed_response(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"candidates": []})

    _mock_httpx_client(monkeypatch, handler)
    provider = GeminiProvider(api_key="g-key", model="gemini-2.0-flash")
    assert provider.synthesize({"event_type": "flood"}) is None


def test_gemini_synthesize_returns_none_on_non_json_text(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": "not json"}]}}]},
        )

    _mock_httpx_client(monkeypatch, handler)
    provider = GeminiProvider(api_key="g-key", model="gemini-2.0-flash")
    assert provider.synthesize({"event_type": "flood"}) is None
