from __future__ import annotations

import os
import secrets
import base64

os.environ.setdefault(
    "DATABASE_URL",
    f"postgresql+asyncpg://test:{secrets.token_urlsafe(24)}@localhost/ravenstore_test",
)
os.environ.setdefault("JWT_SECRET_KEY", secrets.token_urlsafe(48))
os.environ.setdefault("JWT_REFRESH_SECRET_KEY", secrets.token_urlsafe(48))
os.environ.setdefault("ENCRYPTION_KEY", base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())
os.environ.setdefault("API_KEY_PEPPER", secrets.token_urlsafe(48))
os.environ.setdefault("BSC_SCAN_API_KEY", "test-bsc-key")
os.environ.setdefault("TELEGRAM_SERVICE_API_KEY", secrets.token_urlsafe(48))
