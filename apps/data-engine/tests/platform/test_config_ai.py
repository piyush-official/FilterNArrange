import pytest

from filternarrange_engine.platform.config import AiSettings, load_ai_settings


_ENV_VARS = [
    "AI_MAX_CONCURRENT",
    "OLLAMA_BASE_URL",
    "OLLAMA_TIMEOUT_SECONDS",
    "NL2FILTER_MODEL",
    "SUMMARY_MODEL",
    "CHART_MODEL",
    "ANOMALY_MODEL",
    "FILTERNARRANGE_DISABLED_AI",
    "AI_CACHE_TTL_SECONDS",
]


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in _ENV_VARS:
        monkeypatch.delenv(k, raising=False)


def test_defaults():
    s = load_ai_settings()
    assert isinstance(s, AiSettings)
    assert s.max_concurrent == 4
    assert s.ollama_base_url == "http://ollama:11434"
    assert s.ollama_timeout_seconds == 30
    assert s.models["nl_to_filter"] == "qwen2.5:7b"
    assert s.models["auto_summary"] == "llama3.1:8b"
    assert s.models["chart_suggest"] == "llama3.1:8b"
    assert s.models["anomaly_detect"] == "llama3.1:8b"
    assert s.disabled == frozenset()
    assert s.cache_ttl_seconds == 3600


def test_disabled_parses_csv(monkeypatch):
    monkeypatch.setenv("FILTERNARRANGE_DISABLED_AI", "anomaly_detect, chart_suggest ")
    s = load_ai_settings()
    assert s.disabled == frozenset({"anomaly_detect", "chart_suggest"})


def test_overrides(monkeypatch):
    monkeypatch.setenv("AI_MAX_CONCURRENT", "8")
    monkeypatch.setenv("NL2FILTER_MODEL", "qwen2.5:14b")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    s = load_ai_settings()
    assert s.max_concurrent == 8
    assert s.models["nl_to_filter"] == "qwen2.5:14b"
    assert s.ollama_base_url == "http://localhost:11434"
