from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_liveness_has_security_headers() -> None:
    with TestClient(app) as client:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["content-security-policy"] == "default-src 'none'; frame-ancestors 'none'"
    assert response.headers["x-request-id"]


def test_oversized_requests_fail_before_route_processing() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/login",
            headers={"Content-Length": str(50 * 1024 * 1024)},
            content=b"{}",
        )

    assert response.status_code == 413
    assert response.json()["error"]["message_key"] == "validation.request_too_large"
