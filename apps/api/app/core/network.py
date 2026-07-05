from __future__ import annotations

from ipaddress import ip_address, ip_network

from starlette.requests import Request

from app.core.config import settings
from app.core.security import hash_secret


def client_ip(request: Request) -> str:
    direct = request.client.host if request.client else "unknown"
    if direct == "unknown" or not _is_trusted_proxy(direct):
        return direct
    forwarded = request.headers.get("X-Forwarded-For", "")
    candidates = [value.strip() for value in forwarded.split(",") if value.strip()]
    return candidates[0] if candidates else direct


def client_ip_hash(request: Request) -> str:
    return hash_secret(client_ip(request))


def is_allowlisted(request: Request, cidrs: list[str] | None = None) -> bool:
    rules = cidrs if cidrs is not None else settings.sensitive_service_allowlist
    if not rules:
        return settings.environment.lower() != "production"
    try:
        address = ip_address(client_ip(request))
        return any(address in ip_network(rule, strict=False) for rule in rules)
    except ValueError:
        return False


def _is_trusted_proxy(value: str) -> bool:
    try:
        address = ip_address(value)
        return any(address in ip_network(rule, strict=False) for rule in settings.trusted_proxy_cidrs)
    except ValueError:
        return False
