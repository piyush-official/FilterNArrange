"""Centralized settings (env-driven)."""
from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class EngineSettings:
    minio_endpoint: str = os.environ.get("MINIO_ENDPOINT", "http://minio:9000")
    minio_access_key: str = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
    minio_secret_key: str = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
    minio_uploads_bucket: str = os.environ.get("MINIO_UPLOADS_BUCKET", "uploads")
    minio_results_bucket: str = os.environ.get("MINIO_RESULTS_BUCKET", "results")
    sample_bytes: int = int(os.environ.get("DETECT_SAMPLE_BYTES", "65536"))


@dataclass(frozen=True)
class AiSettings:
    """Plan E §6 — env-driven knobs for the AI subsystem.

    Capability ids match the entry-point names emitted by each plugin's
    pyproject.toml. ``disabled`` lets ops disable a capability per-deploy
    without redeploying — read from FILTERNARRANGE_DISABLED_AI (CSV).
    """
    max_concurrent: int
    ollama_base_url: str
    ollama_timeout_seconds: int
    models: Mapping[str, str]
    disabled: frozenset[str]
    cache_ttl_seconds: int


_DEFAULT_MODELS = {
    "nl_to_filter":   "qwen2.5:7b",
    "auto_summary":   "llama3.1:8b",
    "chart_suggest":  "llama3.1:8b",
    "anomaly_detect": "llama3.1:8b",
}

_ENV_KEYS = {
    "nl_to_filter":   "NL2FILTER_MODEL",
    "auto_summary":   "SUMMARY_MODEL",
    "chart_suggest":  "CHART_MODEL",
    "anomaly_detect": "ANOMALY_MODEL",
}


def load_ai_settings() -> AiSettings:
    models = {
        cap: os.environ.get(_ENV_KEYS[cap], default)
        for cap, default in _DEFAULT_MODELS.items()
    }
    raw_disabled = os.environ.get("FILTERNARRANGE_DISABLED_AI", "")
    disabled = frozenset(x.strip() for x in raw_disabled.split(",") if x.strip())
    return AiSettings(
        max_concurrent=int(os.environ.get("AI_MAX_CONCURRENT", "4")),
        ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434"),
        ollama_timeout_seconds=int(os.environ.get("OLLAMA_TIMEOUT_SECONDS", "30")),
        models=models,
        disabled=disabled,
        cache_ttl_seconds=int(os.environ.get("AI_CACHE_TTL_SECONDS", "3600")),
    )


__all__ = ["EngineSettings", "AiSettings", "load_ai_settings"]
