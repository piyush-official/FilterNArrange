"""Centralized settings (env-driven)."""
from __future__ import annotations
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class EngineSettings:
    minio_endpoint: str = os.environ.get("MINIO_ENDPOINT", "http://minio:9000")
    minio_access_key: str = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
    minio_secret_key: str = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
    minio_uploads_bucket: str = os.environ.get("MINIO_UPLOADS_BUCKET", "uploads")
    minio_results_bucket: str = os.environ.get("MINIO_RESULTS_BUCKET", "results")
    sample_bytes: int = int(os.environ.get("DETECT_SAMPLE_BYTES", "65536"))


__all__ = ["EngineSettings"]
