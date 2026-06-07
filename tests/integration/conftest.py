"""Boot the docker-compose stack for integration tests.

Plan A defines an infra/docker-compose.yml with: postgres, redis, minio,
gateway, data-engine, frontend. We assume that file exists and `docker compose`
is installed. Tests are skipped when Docker is not available locally.
"""
import shutil
import subprocess
import time
import pathlib
import pytest
import httpx

ROOT = pathlib.Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "infra" / "docker-compose.yml"


def _wait_for_http(url: str, timeout: float = 60.0) -> None:
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = httpx.get(url, timeout=2.0)
            if r.status_code < 500: return
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError(f"timeout waiting for {url}")


@pytest.fixture(scope="session")
def stack():
    if shutil.which("docker") is None:
        pytest.skip("Docker not available; cannot boot compose stack")
    subprocess.run(["docker", "compose", "-f", str(COMPOSE), "up", "-d",
                    "postgres", "redis", "minio", "data-engine", "gateway"],
                   check=True)
    try:
        _wait_for_http("http://localhost:8080/actuator/health")
        _wait_for_http("http://localhost:8000/healthz")
        yield {"gateway": "http://localhost:8080", "engine": "http://localhost:8000"}
    finally:
        subprocess.run(["docker", "compose", "-f", str(COMPOSE), "down", "-v"],
                       check=False)
