from __future__ import annotations

import os
import secrets

os.environ.setdefault("BOT_TOKEN", f"{secrets.randbelow(900000) + 100000}:{secrets.token_urlsafe(32)}")
os.environ.setdefault("API_BASE_URL", "http://localhost:8000/api/v1")
os.environ.setdefault("BOT_MODE", "polling")
os.environ.setdefault("BOT_PUBLIC_USERNAME", f"RavenStoreTest{secrets.randbelow(99999)}Bot")
