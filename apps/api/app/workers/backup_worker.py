from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography.fernet import Fernet

from app.core.config import settings
from app.integrations.supabase_storage import SupabaseStorageClient


@dataclass(frozen=True)
class BackupArtifact:
    path: str
    checksum_sha256: str
    size_bytes: int
    created_at: str
    encrypted: bool
    verified: bool


class BackupWorker:
    async def create_backup(self) -> BackupArtifact:
        backup_dir = Path(settings.backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        plaintext = backup_dir / f"ravenstore-{timestamp}.dump"
        await self._run(
            "pg_dump",
            settings.migration_database_url.replace("+asyncpg", ""),
            "-Fc",
            "-f",
            str(plaintext),
        )
        await self._run("pg_restore", "--list", str(plaintext))

        target = plaintext
        encrypted = False
        if settings.backup_encryption_key:
            target = plaintext.with_suffix(".dump.enc")
            payload = await asyncio.to_thread(plaintext.read_bytes)
            encrypted_payload = Fernet(settings.backup_encryption_key.encode()).encrypt(payload)
            await asyncio.to_thread(target.write_bytes, encrypted_payload)
            plaintext.unlink(missing_ok=True)
            encrypted = True

        checksum = await asyncio.to_thread(self._checksum, target)
        artifact = BackupArtifact(
            path=str(target),
            checksum_sha256=checksum,
            size_bytes=target.stat().st_size,
            created_at=datetime.now(UTC).isoformat(),
            encrypted=encrypted,
            verified=True,
        )
        manifest = target.with_suffix(target.suffix + ".json")
        await asyncio.to_thread(manifest.write_text, json.dumps(asdict(artifact), indent=2), "utf-8")
        storage = SupabaseStorageClient()
        if storage.configured:
            prefix = f"postgres/{datetime.now(UTC):%Y/%m/%d}"
            await storage.upload_file(
                bucket=settings.supabase_backups_bucket,
                object_path=f"{prefix}/{target.name}",
                source=target,
                upsert=False,
            )
            await storage.upload_file(
                bucket=settings.supabase_backups_bucket,
                object_path=f"{prefix}/{manifest.name}",
                source=manifest,
                content_type="application/json",
                upsert=False,
            )
        await self.cleanup()
        return artifact

    async def cleanup(self) -> None:
        cutoff = datetime.now(UTC) - timedelta(days=settings.backup_retention_days)
        directory = Path(settings.backup_dir)
        if not directory.exists():
            return
        for path in directory.glob("ravenstore-*"):
            modified = datetime.fromtimestamp(path.stat().st_mtime, UTC)
            if modified < cutoff:
                path.unlink(missing_ok=True)

    async def _run(self, *command: str) -> None:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(stderr.decode(errors="ignore")[:2000])

    def _checksum(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
