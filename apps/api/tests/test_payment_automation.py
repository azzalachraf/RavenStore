from __future__ import annotations

from decimal import Decimal

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from app.core.config import settings
from app.integrations.payment_verifiers import BinancePayClient, _amount_failure
from app.schemas.payments import PaymentVerificationIn
from app.services.delivery_providers import DeliveryProviderRegistry


def test_payment_submission_normalizes_supported_reference_fields() -> None:
    crypto = PaymentVerificationIn(payment_token="pay_1234567890123456", tx_hash="0xabc123")
    binance = PaymentVerificationIn(
        payment_token="pay_1234567890123456",
        binance_order_id="987654321",
    )

    assert crypto.submitted_reference == "0xabc123"
    assert binance.submitted_reference == "987654321"


def test_exact_amount_matching_rejects_under_and_over_payment() -> None:
    expected = Decimal("15.00000000")

    assert _amount_failure(expected, expected) is None
    assert _amount_failure(Decimal("14.99999999"), expected) == "amount_underpaid"
    assert _amount_failure(Decimal("15.00000001"), expected) == "amount_overpaid"


def test_binance_webhook_signature_is_verified(monkeypatch) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    monkeypatch.setattr(settings, "binance_webhook_public_key", public_key.decode())
    timestamp = "1720000000000"
    nonce = "unique-nonce"
    body = b'{"bizType":"PAY","data":{"merchantTradeNo":"abc"}}'
    signed_payload = timestamp.encode() + b"\n" + nonce.encode() + b"\n" + body + b"\n"
    signature = private_key.sign(signed_payload, padding.PKCS1v15(), hashes.SHA256())

    import base64

    encoded = base64.b64encode(signature).decode()
    client = BinancePayClient()
    assert client.verify_webhook_signature(
        timestamp=timestamp,
        nonce=nonce,
        body=body,
        signature=encoded,
    )
    assert not client.verify_webhook_signature(
        timestamp=timestamp,
        nonce="wrong",
        body=body,
        signature=encoded,
    )


def test_delivery_registry_rejects_unknown_delivery_types() -> None:
    registry = DeliveryProviderRegistry(object())  # type: ignore[arg-type]

    try:
        registry.resolve(delivery_type="unknown", provider_key=None)
    except ValueError as exc:
        assert str(exc) == "delivery.type_not_supported"
    else:
        raise AssertionError("unknown delivery type must not produce a placeholder delivery")
