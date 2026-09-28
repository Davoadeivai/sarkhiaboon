"""
Payment gateways. The active one is chosen by settings.PAYMENT_GATEWAY.

All amounts inside the project are in Toman. Gateways that expect Rial
convert at the boundary (x10), in one place only.
"""
import logging
import secrets
from dataclasses import dataclass, field

import requests
from django.conf import settings
from django.urls import reverse
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


class GatewayError(Exception):
    pass


@dataclass
class PaymentStart:
    authority: str
    payment_url: str
    raw: dict = field(default_factory=dict)


@dataclass
class PaymentVerification:
    success: bool
    ref_id: str = ""
    card_pan: str = ""
    raw: dict = field(default_factory=dict)


class BaseGateway:
    name = "base"

    def start(self, order, amount_toman, callback_url, request=None) -> PaymentStart:
        raise NotImplementedError

    def verify(self, payment, callback_params) -> PaymentVerification:
        raise NotImplementedError


class SandboxGateway(BaseGateway):
    """
    Development gateway: no money moves. The 'payment page' is a small page on
    our own server with 'successful payment' and 'failed payment' buttons.
    """

    name = "sandbox"

    def start(self, order, amount_toman, callback_url, request=None):
        authority = "SANDBOX" + secrets.token_hex(12).upper()
        url = reverse("payment-sandbox", args=[authority])
        if request is not None:
            url = request.build_absolute_uri(url)
        return PaymentStart(authority=authority, payment_url=url, raw={"sandbox": True})

    def verify(self, payment, callback_params):
        ok = callback_params.get("Status") == "OK"
        return PaymentVerification(
            success=ok,
            ref_id=("SB" + secrets.token_hex(4).upper()) if ok else "",
            card_pan="000000******0000" if ok else "",
            raw={"sandbox": True, "status": callback_params.get("Status")},
        )


class ZarinpalGateway(BaseGateway):
    """
    Zarinpal REST API v4.
      request: POST /pg/v4/payment/request.json -> data.code == 100, data.authority
      pay:     redirect the customer to /pg/StartPay/<authority>
      verify:  POST /pg/v4/payment/verify.json  -> data.code 100 (ok) or 101 (already verified)
    Amounts are sent in Rial.
    """

    name = "zarinpal"

    def __init__(self, session=None):
        self.session = session or requests.Session()
        host = "sandbox.zarinpal.com" if settings.ZARINPAL_SANDBOX else "payment.zarinpal.com"
        self.api = f"https://{host}/pg/v4/payment"
        self.start_pay = f"https://{host}/pg/StartPay"

    def _post(self, endpoint, payload):
        if not settings.ZARINPAL_MERCHANT_ID:
            raise GatewayError("ZARINPAL_MERCHANT_ID is not configured.")
        try:
            response = self.session.post(f"{self.api}/{endpoint}.json", json=payload, timeout=20,
                                         headers={"Accept": "application/json"})
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            raise GatewayError(f"Zarinpal unreachable: {exc}") from exc

    def start(self, order, amount_toman, callback_url, request=None):
        body = self._post("request", {
            "merchant_id": settings.ZARINPAL_MERCHANT_ID,
            "amount": amount_toman * 10,
            "callback_url": callback_url,
            "description": f"سفارش {order.number}",
            "metadata": {"mobile": order.recipient_phone, "order_id": order.number},
        })
        data = body.get("data") or {}
        if data.get("code") != 100 or not data.get("authority"):
            raise GatewayError(f"Zarinpal request refused: {body.get('errors') or body}")
        return PaymentStart(authority=data["authority"], payment_url=f"{self.start_pay}/{data['authority']}", raw=body)

    def verify(self, payment, callback_params):
        if callback_params.get("Status") != "OK":
            return PaymentVerification(success=False, raw={"status": callback_params.get("Status")})
        body = self._post("verify", {
            "merchant_id": settings.ZARINPAL_MERCHANT_ID,
            # Always our stored amount, never anything from the callback URL
            "amount": payment.amount * 10,
            "authority": payment.authority,
        })
        data = body.get("data") or {}
        success = data.get("code") in (100, 101)
        return PaymentVerification(
            success=success,
            ref_id=str(data.get("ref_id", "")) if success else "",
            card_pan=data.get("card_pan", "") if success else "",
            raw=body,
        )


def get_gateway() -> BaseGateway:
    return import_string(settings.PAYMENT_GATEWAY)()
