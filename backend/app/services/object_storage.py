"""Private, content-addressed source files on Neon's S3-compatible endpoint."""

from __future__ import annotations

import hashlib
from typing import Any

from backend.app.config import Settings


class EvidenceObjectStorage:
    def __init__(self, settings: Settings) -> None:
        import boto3
        from botocore.config import Config

        if not settings.storage_endpoint or not settings.storage_access_key.get_secret_value() or not settings.storage_secret_key.get_secret_value():
            raise ValueError("Private evidence storage requires endpoint and credentials")
        self.bucket = settings.evidence_bucket
        self.client = boto3.client(
            "s3", endpoint_url=settings.storage_endpoint, region_name=settings.storage_region,
            aws_access_key_id=settings.storage_access_key.get_secret_value(),
            aws_secret_access_key=settings.storage_secret_key.get_secret_value(),
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"},
                          connect_timeout=3, read_timeout=10, retries={"max_attempts": 1}),
        )

    def put(self, data: bytes, content_type: str) -> dict[str, Any]:
        digest = hashlib.sha256(data).hexdigest()
        key = f"evidence/sha256/{digest}"
        try:
            self.client.put_object(Bucket=self.bucket, Key=key, Body=data,
                                   ContentType=content_type, Metadata={"sha256": digest})
        except Exception:
            raise RuntimeError("Private evidence object upload unavailable") from None
        return {"object_key": key, "object_bucket": self.bucket, "size_bytes": len(data)}

    def get(self, key: str, expected_hash: str) -> bytes:
        if key != f"evidence/sha256/{expected_hash}":
            raise ValueError("Evidence object key does not match its provenance hash")
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            with response["Body"] as body:
                data = body.read()
        except Exception:
            raise RuntimeError("Private evidence object download unavailable") from None
        if hashlib.sha256(data).hexdigest() != expected_hash:
            raise ValueError("Evidence object integrity verification failed")
        return data
