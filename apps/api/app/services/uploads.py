from __future__ import annotations

import asyncio
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings
from app.integrations.supabase_storage import SupabaseStorageClient

MAGIC = {
    "application/pdf": (b"%PDF-",),
    "application/zip": (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"),
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/webp": (b"RIFF",),
}


@dataclass(frozen=True)
class QuarantinedUpload:
    upload_id: str
    filename: str
    content_type: str
    size: int
    sha256: str
    scan_status: str
    storage_uri: str | None = None


class UploadValidationError(ValueError):
    pass


class UploadService:
    async def quarantine(
        self,
        upload: UploadFile,
        *,
        bucket: str | None = None,
        object_prefix: str = "quarantine",
    ) -> QuarantinedUpload:
        content_type = (upload.content_type or "").lower()
        if content_type not in settings.upload_allowed_types or content_type not in MAGIC:
            raise UploadValidationError("uploads.unsupported_type")
        filename = self._safe_filename(upload.filename or "upload")
        data = bytearray()
        while chunk := await upload.read(1024 * 1024):
            data.extend(chunk)
            if len(data) > settings.upload_max_bytes:
                raise UploadValidationError("uploads.file_too_large")
        if not any(bytes(data).startswith(signature) for signature in MAGIC[content_type]):
            raise UploadValidationError("uploads.content_type_mismatch")
        if content_type == "image/webp" and bytes(data)[8:12] != b"WEBP":
            raise UploadValidationError("uploads.content_type_mismatch")
        upload_id = uuid4().hex
        directory = Path(settings.upload_quarantine_dir)
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / f"{upload_id}-{filename}"
        await asyncio.to_thread(target.write_bytes, bytes(data))
        scan_status = await self._scan(bytes(data))
        storage_uri = None
        if scan_status == "clean":
            storage_uri = await SupabaseStorageClient().upload_file(
                bucket=bucket or settings.supabase_product_files_bucket,
                object_path=f"{object_prefix}/{upload_id}/{filename}",
                source=target,
                content_type=content_type,
            )
            target.unlink(missing_ok=True)
        return QuarantinedUpload(
            upload_id=upload_id,
            filename=filename,
            content_type=content_type,
            size=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
            scan_status=scan_status,
            storage_uri=storage_uri,
        )

    async def _scan(self, data: bytes) -> str:
        if not settings.clamav_host:
            return "quarantined_unscanned" if settings.upload_require_antivirus else "clean"
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(settings.clamav_host, settings.clamav_port),
            timeout=5,
        )
        try:
            writer.write(b"zINSTREAM\0")
            for offset in range(0, len(data), 64 * 1024):
                chunk = data[offset : offset + 64 * 1024]
                writer.write(len(chunk).to_bytes(4, "big") + chunk)
            writer.write((0).to_bytes(4, "big"))
            await writer.drain()
            response = await asyncio.wait_for(reader.read(4096), timeout=15)
            if b"FOUND" in response:
                raise UploadValidationError("uploads.malware_detected")
            if b"OK" not in response:
                raise UploadValidationError("uploads.scan_failed")
            return "clean"
        finally:
            writer.close()
            await writer.wait_closed()

    def _safe_filename(self, value: str) -> str:
        name = Path(value).name
        normalized = re.sub(r"[^A-Za-z0-9._-]", "_", name)[:180]
        if not normalized or normalized in {".", ".."}:
            raise UploadValidationError("uploads.invalid_filename")
        return normalized
