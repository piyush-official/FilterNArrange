"""MinIO adapter implementing ObjectStorePort."""
from __future__ import annotations
import io
from typing import BinaryIO
from urllib.parse import urlparse

from minio import Minio
from minio.error import S3Error

from filternarrange_engine.platform.config import EngineSettings


class MinioObjectStore:

    def __init__(self, settings: EngineSettings) -> None:
        parsed = urlparse(settings.minio_endpoint)
        secure = parsed.scheme == "https"
        self._client = Minio(
            parsed.netloc,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=secure,
        )

    def ensure_bucket(self, bucket: str) -> None:
        if not self._client.bucket_exists(bucket):
            self._client.make_bucket(bucket)

    def _split(self, ref: str) -> tuple[str, str]:
        slash = ref.find("/")
        if slash < 0:
            raise ValueError(f"ref '{ref}' is not in bucket/key form")
        return ref[:slash], ref[slash + 1:]

    def get(self, ref: str) -> BinaryIO:
        bucket, key = self._split(ref)
        try:
            response = self._client.get_object(bucket, key)
            data = response.read()
            response.close()
            response.release_conn()
            return io.BytesIO(data)
        except S3Error as e:
            raise FileNotFoundError(f"object not found: {ref}") from e

    def put(self, ref: str, data: BinaryIO, size: int, content_type: str) -> None:
        bucket, key = self._split(ref)
        self.ensure_bucket(bucket)
        self._client.put_object(bucket, key, data, length=size, content_type=content_type)


__all__ = ["MinioObjectStore"]
