from __future__ import annotations

import os
from decimal import Decimal
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.main import app

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS") != "1",
    reason="requires migrated PostgreSQL and Redis services",
)

def test_wallet_summary_and_topup() -> None:
    email = f"wallet-{uuid4().hex}@example.com"
    with TestClient(app) as client:
        # Register user
        reg = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "correct-horse-battery-staple", "locale": "en"},
        )
        assert reg.status_code == 201
        user_data = reg.json()
        access_token = user_data["access_token"]

        # Check initial wallet summary
        summary = client.get(
            "/api/v1/wallet/summary",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert summary.status_code == 200
        data = summary.json()
        assert data["future_balance"] == 0.0
        assert data["currency"] == "USD"

        # Create wallet top-up request
        topup = client.post(
            "/api/v1/wallet/topup",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"amount": 25.50, "method": "usdt_trc20"}
        )
        assert topup.status_code == 201
        resp = topup.json()
        assert "payment" in resp
        assert resp["payment"]["amount"] == "25.50000000"
        assert resp["payment"]["currency"] == "USDT"
