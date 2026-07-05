from __future__ import annotations

import mimetypes
import asyncio
from pathlib import Path, PurePosixPath
from urllib.parse import quote

import httpx

from app.core.config import settings
from app.core.resilience import call_with_resilience


class SupabaseStorageError(RuntimeError):
    pass


class SupabaseStorageClient:
    @property
    def configured(self) -> bool:
        return bool(settings.supabase_project_url and settings.supabase_service_role_key)

    async def upload_file(
        self,
        *,
        bucket: str,
        object_path: str,
        source: Path,
        content_type: str | None = None,
        upsert: bool = False,
    ) -> str:
        self._require_configuration()
        normalized = self._normalize_path(object_path)
        media_type = content_type or mimetypes.guess_type(source.name)[0] or "application/octet-stream"

        async def perform() -> httpx.Response:
            async with httpx.AsyncClient(timeout=settings.external_http_timeout_seconds) as client:
                response = await client.post(
                    self._object_url(bucket, normalized),
                    content=self._stream_file(source),
                    headers={**self._headers(), "Content-Type": media_type, "x-upsert": str(upsert).lower()},
                )
                if response.status_code >= 500:
                    response.raise_for_status()
                return response

        response = await call_with_resilience(
            "supabase-storage",
            perform,
            retryable=lambda exc: isinstance(exc, (httpx.TimeoutException, httpx.NetworkError))
            or isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code >= 500,
        )
        if not response.is_success:
            raise SupabaseStorageError(f"storage.upload_failed:{response.status_code}")
        return f"supabase://{bucket}/{normalized}"

    async def create_signed_url(self, storage_uri: str, expires_in: int = 900) -> str:
        bucket, object_path = self.parse_uri(storage_uri)
        self._require_configuration()
        url = f"{str(settings.supabase_project_url).rstrip('/')}/storage/v1/object/sign/{quote(bucket)}/{quote(object_path)}"

        async def perform() -> httpx.Response:
            async with httpx.AsyncClient(timeout=settings.external_http_timeout_seconds) as client:
                response = await client.post(url, json={"expiresIn": expires_in}, headers=self._headers())
                if response.status_code >= 500:
                    response.raise_for_status()
                return response

        response = await call_with_resilience("supabase-storage", perform)
        if not response.is_success:
            raise SupabaseStorageError(f"storage.sign_failed:{response.status_code}")
        signed_path = response.json().get("signedURL") or response.json().get("signedUrl")
        if not signed_path:
            raise SupabaseStorageError("storage.sign_response_invalid")
        if str(signed_path).startswith("http"):
            return str(signed_path)
        return f"{str(settings.supabase_project_url).rstrip('/')}/storage/v1{signed_path}"

    def public_url(self, *, bucket: str, object_path: str) -> str:
        self._require_configuration()
        normalized = self._normalize_path(object_path)
        return f"{str(settings.supabase_project_url).rstrip('/')}/storage/v1/object/public/{quote(bucket)}/{quote(normalized)}"

    def parse_uri(self, storage_uri: str) -> tuple[str, str]:
        if not storage_uri.startswith("supabase://"):
            raise SupabaseStorageError("storage.uri_invalid")
        value = storage_uri.removeprefix("supabase://")
        bucket, separator, object_path = value.partition("/")
        if not separator or not bucket or not object_path:
            raise SupabaseStorageError("storage.uri_invalid")
        return bucket, self._normalize_path(object_path)

    def _headers(self) -> dict[str, str]:
        key = settings.supabase_service_role_key
        if key is None:
            raise SupabaseStorageError("storage.not_configured")
        secret = key.get_secret_value()
        return {"apikey": secret, "Authorization": f"Bearer {secret}"}

    def _object_url(self, bucket: str, object_path: str) -> str:
        return f"{str(settings.supabase_project_url).rstrip('/')}/storage/v1/object/{quote(bucket)}/{quote(object_path)}"

    def _normalize_path(self, value: str) -> str:
        path = PurePosixPath(value.replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise SupabaseStorageError("storage.path_invalid")
        return str(path)

    def _require_configuration(self) -> None:
        if not self.configured:
            raise SupabaseStorageError("storage.not_configured")

    async def _stream_file(self, path: Path):
        with path.open("rb") as handle:
            while chunk := await asyncio.to_thread(handle.read, 1024 * 1024):
                yield chunk
