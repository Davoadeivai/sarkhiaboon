"""
SMS delivery for login codes.

The active backend is chosen by settings.SMS_BACKEND, so switching SMS
providers never touches the login logic.
"""
import logging

import requests
from django.conf import settings
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


class SMSDeliveryError(Exception):
    pass


class BaseSMSBackend:
    def send_otp(self, phone, code):
        raise NotImplementedError


class ConsoleSMSBackend(BaseSMSBackend):
    """Development backend: writes the code to the server log instead of sending it."""

    def send_otp(self, phone, code):
        logger.warning("OTP for %s: %s", phone, code)


class LocMemSMSBackend(BaseSMSBackend):
    """Test backend: keeps sent codes in memory (LocMemSMSBackend.outbox)."""

    outbox = []

    def send_otp(self, phone, code):
        LocMemSMSBackend.outbox.append({"phone": phone, "code": code})


class KavenegarSMSBackend(BaseSMSBackend):
    """
    Kavenegar "verify/lookup" API. The message text is defined as a template in
    the Kavenegar panel (template name in KAVENEGAR_OTP_TEMPLATE) and must
    contain the %token placeholder.
    """

    url = "https://api.kavenegar.com/v1/{key}/verify/lookup.json"

    def send_otp(self, phone, code):
        if not settings.KAVENEGAR_API_KEY:
            raise SMSDeliveryError("KAVENEGAR_API_KEY is not configured.")
        try:
            response = requests.post(
                self.url.format(key=settings.KAVENEGAR_API_KEY),
                data={"receptor": phone, "token": code, "template": settings.KAVENEGAR_OTP_TEMPLATE},
                timeout=10,
            )
        except requests.RequestException as exc:
            raise SMSDeliveryError(str(exc)) from exc
        if response.status_code != 200:
            raise SMSDeliveryError(f"Kavenegar returned HTTP {response.status_code}: {response.text[:200]}")


def get_sms_backend():
    return import_string(settings.SMS_BACKEND)()
