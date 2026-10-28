"""Private object storage must preserve and verify synthetic source bytes."""

import hashlib
from io import BytesIO
from unittest.mock import Mock, patch

import pytest

from backend.app.services.object_storage import EvidenceObjectStorage
from backend.app.config import Settings


def test_storage_validates_configuration_but_defers_client_until_first_operation():
    cfg = Settings(_env_file=None, AWS_ENDPOINT_URL_S3="https://synthetic.invalid",
                   AWS_ACCESS_KEY_ID="synthetic-only", AWS_SECRET_ACCESS_KEY="synthetic-only")
    with patch("boto3.client") as factory:
        service = EvidenceObjectStorage(cfg)
        factory.assert_not_called()
        assert service.client is service.client
        factory.assert_called_once()
    with pytest.raises(ValueError, match="requires endpoint and credentials"):
        EvidenceObjectStorage(Settings(_env_file=None, AWS_ENDPOINT_URL_S3="",
                                       AWS_ACCESS_KEY_ID="", AWS_SECRET_ACCESS_KEY=""))


def storage() -> EvidenceObjectStorage:
    service = EvidenceObjectStorage.__new__(EvidenceObjectStorage)
    service.bucket = "object"
    service.client = Mock()
    return service


def test_upload_is_content_addressed_without_public_acl():
    service = storage()
    data = b"Synthetic FIR fixture"
    digest = hashlib.sha256(data).hexdigest()
    result = service.put(data, "text/plain")
    assert result["object_key"] == f"evidence/sha256/{digest}"
    service.client.put_object.assert_called_once_with(
        Bucket="object", Key=result["object_key"], Body=data,
        ContentType="text/plain", Metadata={"sha256": digest},
    )


def test_download_checks_provenance_before_and_after_storage_read():
    service = storage()
    data = b"Synthetic FIR fixture"
    digest = hashlib.sha256(data).hexdigest()
    with pytest.raises(ValueError, match="provenance hash"):
        service.get("unrelated-key", digest)
    service.client.get_object.assert_not_called()
    service.client.get_object.return_value = {"Body": BytesIO(data)}
    assert service.get(f"evidence/sha256/{digest}", digest) == data
    service.client.get_object.return_value = {"Body": BytesIO(b"altered")}
    with pytest.raises(ValueError, match="integrity"):
        service.get(f"evidence/sha256/{digest}", digest)


def test_storage_failures_do_not_expose_provider_details():
    service = storage()
    service.client.put_object.side_effect = RuntimeError("secret credential")
    with pytest.raises(RuntimeError, match="^Private evidence object upload unavailable$"):
        service.put(b"synthetic", "text/plain")
