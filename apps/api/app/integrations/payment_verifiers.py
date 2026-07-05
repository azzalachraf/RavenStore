from __future__ import annotations

import asyncio
import base64
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha512
from typing import Any

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from app.core.config import settings
from app.core.resilience import call_with_resilience
from app.services.configuration import NetworkConfiguration

TRANSFER_TOPIC = "ddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


@dataclass(frozen=True)
class VerificationResult:
    matched: bool
    confirmations: int
    amount: Decimal
    raw_payload: dict[str, Any]
    status: str
    failure_code: str | None = None
    sender: str | None = None
    provider_reference: str | None = None


class CryptoPaymentVerifier:
    async def verify(
        self,
        *,
        configuration: NetworkConfiguration,
        tx_hash: str,
        expected_amount: Decimal,
    ) -> VerificationResult:
        if configuration.network == "USDT_TRC20":
            return await self._verify_trc20(configuration, tx_hash, expected_amount)
        if configuration.network == "USDT_BEP20":
            return await self._verify_bep20(configuration, tx_hash, expected_amount)
        raise ValueError("payments.unsupported_method")

    async def _verify_trc20(
        self,
        configuration: NetworkConfiguration,
        tx_hash: str,
        expected_amount: Decimal,
    ) -> VerificationResult:
        if not configuration.address or not configuration.contract_address:
            raise ValueError("payments.network_not_configured")
        headers = {"TRON-PRO-API-KEY": configuration.api_key} if configuration.api_key else {}
        async with httpx.AsyncClient(timeout=20) as client:
            receipt_response, events_response, block_response = await _gather_http(
                client.post("https://api.trongrid.io/wallet/gettransactioninfobyid", json={"value": tx_hash}, headers=headers),
                client.get(
                    f"https://api.trongrid.io/v1/transactions/{tx_hash}/events",
                    params={"only_confirmed": "true"},
                    headers=headers,
                ),
                client.post("https://api.trongrid.io/wallet/getnowblock", json={}, headers=headers),
            )
        receipt = receipt_response.json()
        events_payload = events_response.json()
        current_block_payload = block_response.json()
        raw = {"receipt": receipt, "events": events_payload}
        if not receipt or receipt.get("receipt", {}).get("result") != "SUCCESS":
            return VerificationResult(False, 0, Decimal("0"), raw, "pending", "receipt_not_confirmed")
        receipt_block = int(receipt.get("blockNumber", 0))
        current_block = int(current_block_payload.get("block_header", {}).get("raw_data", {}).get("number", receipt_block))
        confirmations = max(0, current_block - receipt_block + 1)
        for event in events_payload.get("data", []):
            result = event.get("result") or {}
            if event.get("event_name") != "Transfer" or event.get("_unconfirmed") is True:
                continue
            if not _same_address(event.get("contract_address"), configuration.contract_address):
                continue
            if not _same_address(result.get("to"), configuration.address):
                continue
            amount = Decimal(str(result.get("value", "0"))) / (Decimal(10) ** configuration.decimals)
            failure = _amount_failure(amount, expected_amount)
            if failure:
                return VerificationResult(False, confirmations, amount, raw, "mismatched", failure, result.get("from"), tx_hash)
            if confirmations < configuration.required_confirmations:
                return VerificationResult(False, confirmations, amount, raw, "confirming", "insufficient_confirmations", result.get("from"), tx_hash)
            return VerificationResult(True, confirmations, amount, raw, "confirmed", sender=result.get("from"), provider_reference=tx_hash)
        return VerificationResult(False, confirmations, Decimal("0"), raw, "mismatched", "transfer_not_found", provider_reference=tx_hash)

    async def _verify_bep20(
        self,
        configuration: NetworkConfiguration,
        tx_hash: str,
        expected_amount: Decimal,
    ) -> VerificationResult:
        if not configuration.address or not configuration.contract_address or not configuration.api_key:
            raise ValueError("payments.network_not_configured")
        base_params = {"chainid": "56", "apikey": configuration.api_key}
        async with httpx.AsyncClient(timeout=20) as client:
            receipt_response, block_response = await _gather_http(
                client.get(
                    "https://api.etherscan.io/v2/api",
                    params={**base_params, "module": "proxy", "action": "eth_getTransactionReceipt", "txhash": tx_hash},
                ),
                client.get(
                    "https://api.etherscan.io/v2/api",
                    params={**base_params, "module": "proxy", "action": "eth_blockNumber"},
                ),
            )
        receipt_payload = receipt_response.json()
        block_payload = block_response.json()
        receipt = receipt_payload.get("result") or {}
        raw = {"receipt": receipt_payload, "block": block_payload}
        if receipt.get("status") != "0x1":
            return VerificationResult(False, 0, Decimal("0"), raw, "pending", "receipt_not_confirmed", provider_reference=tx_hash)
        receipt_block = int(receipt.get("blockNumber", "0x0"), 16)
        current_block = int(block_payload.get("result", "0x0"), 16)
        confirmations = max(0, current_block - receipt_block + 1)
        expected_contract = _normalize_evm_address(configuration.contract_address)
        expected_recipient = _normalize_evm_address(configuration.address)
        for log in receipt.get("logs", []):
            topics = [str(topic).removeprefix("0x").lower() for topic in log.get("topics", [])]
            if len(topics) < 3 or topics[0] != TRANSFER_TOPIC:
                continue
            if _normalize_evm_address(log.get("address")) != expected_contract:
                continue
            recipient = _normalize_evm_address(f"0x{topics[2][-40:]}")
            if recipient != expected_recipient:
                continue
            amount = Decimal(int(str(log.get("data", "0x0")), 16)) / (Decimal(10) ** configuration.decimals)
            sender = _normalize_evm_address(f"0x{topics[1][-40:]}")
            failure = _amount_failure(amount, expected_amount)
            if failure:
                return VerificationResult(False, confirmations, amount, raw, "mismatched", failure, sender, tx_hash)
            if confirmations < configuration.required_confirmations:
                return VerificationResult(False, confirmations, amount, raw, "confirming", "insufficient_confirmations", sender, tx_hash)
            return VerificationResult(True, confirmations, amount, raw, "confirmed", sender=sender, provider_reference=tx_hash)
        return VerificationResult(False, confirmations, Decimal("0"), raw, "mismatched", "transfer_not_found", provider_reference=tx_hash)


class BinancePayClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        api_secret: str | None = None,
        webhook_public_key: str | None = None,
        base_url: str | None = None,
    ):
        self.api_key = api_key or settings.binance_api_key
        self.api_secret = api_secret or settings.binance_api_secret
        self.webhook_public_key = webhook_public_key or settings.binance_webhook_public_key
        self.base_url = (base_url or settings.binance_pay_base_url).rstrip("/")

    async def create_order(
        self,
        *,
        merchant_trade_no: str,
        amount: Decimal,
        currency: str,
        product_name: str,
    ) -> dict[str, Any]:
        body = {
            "env": {"terminalType": "OTHERS"},
            "merchantTradeNo": merchant_trade_no,
            "orderAmount": str(amount),
            "currency": currency,
            "goods": {
                "goodsType": "02",
                "goodsCategory": "D000",
                "referenceGoodsId": merchant_trade_no,
                "goodsName": product_name[:256],
            },
        }
        return await self._signed_request("/binancepay/openapi/v3/order", body)

    async def verify_order(
        self,
        *,
        merchant_trade_no: str,
        expected_amount: Decimal,
        submitted_reference: str | None = None,
    ) -> VerificationResult:
        body: dict[str, str] = {"merchantTradeNo": merchant_trade_no}
        if submitted_reference and submitted_reference.isdigit():
            body["prepayId"] = submitted_reference
        payload = await self._signed_request("/binancepay/openapi/v2/order/query", body)
        data = payload.get("data") or {}
        amount = Decimal(str(data.get("totalFee", data.get("orderAmount", "0"))))
        paid = data.get("status") == "PAID"
        failure = _amount_failure(amount, expected_amount) if paid else None
        matched = paid and failure is None
        return VerificationResult(
            matched,
            1 if paid else 0,
            amount,
            payload,
            "confirmed" if matched else "mismatched" if failure else "pending",
            failure_code=failure,
            provider_reference=str(data.get("prepayId") or submitted_reference or merchant_trade_no),
        )

    def verify_webhook_signature(self, *, timestamp: str, nonce: str, body: bytes, signature: str) -> bool:
        if not self.webhook_public_key:
            return False
        public_key = serialization.load_pem_public_key(self.webhook_public_key.encode())
        payload = timestamp.encode() + b"\n" + nonce.encode() + b"\n" + body + b"\n"
        try:
            public_key.verify(base64.b64decode(signature), payload, padding.PKCS1v15(), hashes.SHA256())
            return True
        except (InvalidSignature, ValueError):
            return False

    async def _signed_request(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key or not self.api_secret:
            raise ValueError("payments.binance_not_configured")
        timestamp = str(int(time.time() * 1000))
        nonce = secrets.token_hex(16)
        body_text = json.dumps(body, separators=(",", ":"), ensure_ascii=False)
        payload = f"{timestamp}\n{nonce}\n{body_text}\n"
        signature = hmac.new(self.api_secret.encode(), payload.encode(), sha512).hexdigest().upper()
        headers = {
            "BinancePay-Timestamp": timestamp,
            "BinancePay-Nonce": nonce,
            "BinancePay-Certificate-SN": self.api_key,
            "BinancePay-Signature": signature,
            "Content-Type": "application/json",
        }
        async def perform() -> dict[str, Any]:
            async with httpx.AsyncClient(timeout=settings.external_http_timeout_seconds) as client:
                response = await client.post(f"{self.base_url}{path}", content=body_text.encode(), headers=headers)
                response.raise_for_status()
                return response.json()

        result = await call_with_resilience(
            "binance-pay",
            perform,
            retryable=lambda exc: isinstance(exc, (httpx.TimeoutException, httpx.NetworkError))
            or isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code >= 500,
        )
        if result.get("status") == "FAIL" or result.get("code") not in {None, "000000", "SUCCESS"}:
            raise ValueError(f"payments.binance_error:{result.get('code', 'unknown')}")
        return result


async def _gather_http(*calls):
    responses = await asyncio.gather(*calls)
    for response in responses:
        response.raise_for_status()
    return responses


def _amount_failure(actual: Decimal, expected: Decimal) -> str | None:
    if actual < expected:
        return "amount_underpaid"
    if actual > expected:
        return "amount_overpaid"
    return None


def _same_address(left: str | None, right: str | None) -> bool:
    if not left or not right:
        return False
    return left == right or left.lower().removeprefix("0x") == right.lower().removeprefix("0x")


def _normalize_evm_address(value: str | None) -> str:
    if not value:
        return ""
    normalized = value.lower().removeprefix("0x")
    return f"0x{normalized[-40:]}"
