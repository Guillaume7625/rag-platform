"""MinIO / S3 object storage wrapper."""
from __future__ import annotations

import io
import uuid

from minio import Minio
from minio.error import S3Error

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


class StorageService:
    def __init__(self) -> None:
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self.bucket = settings.minio_bucket
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
        except S3Error as e:
            log.warning("minio_bucket_check_failed", error=str(e))

    def put_object(self, tenant_id: uuid.UUID, filename: str, data: bytes, content_type: str) -> str:
        key = f"{tenant_id}/{uuid.uuid4()}/{filename}"
        self.client.put_object(
            self.bucket,
            key,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        return key

    def get_object(self, key: str) -> bytes:
        resp = self.client.get_object(self.bucket, key)
        try:
            return resp.read()
        finally:
            resp.close()
            resp.release_conn()

    def delete_object(self, key: str) -> None:
        try:
            self.client.remove_object(self.bucket, key)
        except S3Error as e:
            log.warning("minio_delete_failed", key=key, error=str(e))


_storage: StorageService | None = None


def get_storage() -> StorageService:
    global _storage
    if _storage is None:
        _storage = StorageService()
    return _storage
