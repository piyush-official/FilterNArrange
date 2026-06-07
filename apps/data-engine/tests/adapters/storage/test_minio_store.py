import io
import os
import shutil
import socket
import time
import subprocess
import pytest

from filternarrange_engine.adapters.storage.minio_store import MinioObjectStore
from filternarrange_engine.platform.config import EngineSettings


pytestmark = pytest.mark.skipif(
    shutil.which("docker") is None,
    reason="Docker not available; MinIO container cannot start",
)


def _free_port():
    s = socket.socket()
    s.bind(("localhost", 0))
    p = s.getsockname()[1]
    s.close()
    return p


@pytest.fixture(scope="module")
def minio_server():
    port = _free_port()
    console_port = _free_port()
    proc = subprocess.Popen([
        "docker", "run", "--rm", "-d",
        "-p", f"{port}:9000",
        "-p", f"{console_port}:9001",
        "-e", "MINIO_ROOT_USER=testkey",
        "-e", "MINIO_ROOT_PASSWORD=testsecret",
        "minio/minio:RELEASE.2024-08-29T01-40-52Z",
        "server", "/data", "--console-address", ":9001"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    cid = proc.stdout.read().decode().strip()
    time.sleep(3)
    try:
        yield f"http://localhost:{port}"
    finally:
        subprocess.run(["docker", "rm", "-f", cid], check=False)


def test_put_get_roundtrip(minio_server):
    settings = EngineSettings(
        minio_endpoint=minio_server,
        minio_access_key="testkey",
        minio_secret_key="testsecret",
        minio_uploads_bucket="uploads",
    )
    store = MinioObjectStore(settings)
    store.ensure_bucket("uploads")
    body = b"name,age\nA,1\n"
    store.put("uploads/x.csv", io.BytesIO(body), len(body), "text/csv")
    out = store.get("uploads/x.csv").read()
    assert out == body
