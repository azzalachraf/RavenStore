from __future__ import annotations

from io import BytesIO
from uuid import uuid4

import pytest
import bcrypt
from starlette.datastructures import Headers, UploadFile

from app.core.config import settings
from app.core.resilience import CircuitBreaker, CircuitOpenError, call_with_resilience
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.services.uploads import UploadService, UploadValidationError
from app.integrations.supabase_storage import SupabaseStorageClient, SupabaseStorageError


def test_passwords_use_argon2_and_verify() -> None:
    encoded = hash_password("a-commercial-grade-passphrase")

    assert encoded.startswith("$argon2")
    assert verify_password("a-commercial-grade-passphrase", encoded)
    assert not verify_password("wrong-password", encoded)


def test_legacy_bcrypt_passwords_remain_verifiable_for_migration() -> None:
    encoded = bcrypt.hashpw(b"legacy-password", bcrypt.gensalt(rounds=12)).decode()

    assert verify_password("legacy-password", encoded)
    assert not verify_password("wrong-password", encoded)


def test_access_and_refresh_tokens_are_bound_to_session_issuer_and_audience() -> None:
    user_id = uuid4()
    session_id = uuid4()
    access = create_access_token(user_id, "Customer", session_id=session_id)
    refresh, _, token_id = create_refresh_token(user_id, session_id=session_id)

    access_payload = decode_access_token(access)
    refresh_payload = decode_refresh_token(refresh)
    assert access_payload["sub"] == str(user_id)
    assert access_payload["sid"] == str(session_id)
    assert access_payload["iss"] == settings.jwt_issuer
    assert refresh_payload["jti"] == token_id
    assert refresh_payload["aud"] == settings.jwt_audience


async def test_resilience_retries_transient_failures() -> None:
    attempts = 0

    async def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise TimeoutError("temporary")
        return "ok"

    assert await call_with_resilience("test-retry", operation, attempts=3) == "ok"
    assert attempts == 3


async def test_circuit_breaker_opens_after_threshold() -> None:
    breaker = CircuitBreaker(failure_threshold=2, recovery_seconds=60)

    async def failure() -> None:
        raise TimeoutError("downstream unavailable")

    with pytest.raises(TimeoutError):
        await breaker.call(failure)
    with pytest.raises(TimeoutError):
        await breaker.call(failure)
    with pytest.raises(CircuitOpenError):
        await breaker.call(failure)


async def test_upload_pipeline_quarantines_valid_pdf(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(settings, "upload_quarantine_dir", str(tmp_path))
    monkeypatch.setattr(settings, "clamav_host", None)
    monkeypatch.setattr(settings, "upload_require_antivirus", True)
    settings.__dict__["upload_allowed_types"] = {"application/pdf", "application/zip"}
    upload = UploadFile(
        file=BytesIO(b"%PDF-1.7\nsecure-test"),
        filename="../../invoice.pdf",
        headers=Headers({"content-type": "application/pdf"}),
    )

    artifact = await UploadService().quarantine(upload)

    assert artifact.filename == "invoice.pdf"
    assert artifact.scan_status == "quarantined_unscanned"
    assert artifact.size > 0
    assert len(artifact.sha256) == 64


async def test_upload_pipeline_rejects_spoofed_content(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(settings, "upload_quarantine_dir", str(tmp_path))
    settings.__dict__["upload_allowed_types"] = {"application/pdf", "application/zip"}
    upload = UploadFile(
        file=BytesIO(b"not-a-pdf"),
        filename="payload.pdf",
        headers=Headers({"content-type": "application/pdf"}),
    )

    with pytest.raises(UploadValidationError, match="uploads.content_type_mismatch"):
        await UploadService().quarantine(upload)


def test_supabase_storage_uri_rejects_path_traversal() -> None:
    storage = SupabaseStorageClient()

    assert storage.parse_uri("supabase://product-files/orders/receipt.pdf") == (
        "product-files",
        "orders/receipt.pdf",
    )
    with pytest.raises(SupabaseStorageError, match="storage.path_invalid"):
        storage.parse_uri("supabase://product-files/../backups/database.dump")
