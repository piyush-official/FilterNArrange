# SPDX-License-Identifier: Apache-2.0
"""FastAPI application entrypoint and /health endpoint."""

from fastapi import FastAPI

app = FastAPI(
    title="FilterNArrange data-engine",
    version="0.0.0",
    docs_url="/docs",
    redoc_url=None,
)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe — returns {'status': 'UP'} when the process is serving."""
    return {"status": "UP"}
