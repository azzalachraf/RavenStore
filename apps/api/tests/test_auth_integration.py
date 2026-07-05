from __future__ import annotations

import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS") != "1",
    reason="requires migrated PostgreSQL and Redis services",
)


def test_refresh_rotation_reuse_revokes_the_session_family() -> None:
    email = f"security-{uuid4().hex}@example.com"
    with TestClient(app) as client:
        registered = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "correct-horse-battery-staple", "locale": "en"},
        )
        assert registered.status_code == 201
        original = registered.json()

        rotated = client.post("/api/v1/auth/refresh", json={"refresh_token": original["refresh_token"]})
        assert rotated.status_code == 200
        current = rotated.json()
        assert current["refresh_token"] != original["refresh_token"]

        reuse = client.post("/api/v1/auth/refresh", json={"refresh_token": original["refresh_token"]})
        assert reuse.status_code == 401
        assert reuse.json()["error"]["message_key"] == "auth.session_compromised"

        revoked_access = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {current['access_token']}"},
        )
        assert revoked_access.status_code == 401


def test_telegram_service_bootstraps_api_owned_customer() -> None:
    telegram_id = int(f"9{uuid4().int % 10**12:012d}")
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/telegram/session",
            headers={"X-API-Key": os.environ["TELEGRAM_SERVICE_API_KEY"]},
            json={
                "telegram_id": telegram_id,
                "username": f"integration_{telegram_id}",
                "first_name": "Raven",
                "last_name": "Customer",
                "language_code": "ar",
            },
        )
        assert response.status_code == 200
        session = response.json()
        assert session["locale"] == "ar"

        profile = client.get(
            "/api/v1/telegram/users/me",
            headers={"Authorization": f"Bearer {session['access_token']}"},
        )
        assert profile.status_code == 200
        assert profile.json()["telegram_id"] == telegram_id
