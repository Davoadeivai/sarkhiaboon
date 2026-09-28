"""
Login business logic, kept out of the views so it can be tested and reused.
"""
import hashlib
import hmac
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import OTPCode, User
from .phone import normalize_phone
from .signals import guest_merged
from .sms import SMSDeliveryError, get_sms_backend

logger = logging.getLogger(__name__)


class OTPError(Exception):
    """Raised with a user-facing Persian message."""


class OTPCooldownError(OTPError):
    """A new code was requested too soon after the previous one."""


class OTPDeliveryError(OTPError):
    """The SMS provider could not deliver the code."""


def _hash_code(phone, code):
    key = settings.SECRET_KEY.encode()
    return hmac.new(key, f"{phone}:{code}".encode(), hashlib.sha256).hexdigest()


def _generate_code():
    length = settings.OTP_LENGTH
    return "".join(secrets.choice("0123456789") for _ in range(length))


def request_otp(raw_phone):
    """
    Create and send a login code. Enforces a resend cooldown per phone number.
    Returns the number of seconds the code stays valid.
    """
    phone = normalize_phone(raw_phone)
    now = timezone.now()
    cooldown = timedelta(seconds=settings.OTP_RESEND_COOLDOWN_SECONDS)

    last = OTPCode.objects.filter(phone=phone).order_by("-created_at").first()
    if last and now - last.created_at < cooldown:
        wait = int((cooldown - (now - last.created_at)).total_seconds()) + 1
        raise OTPCooldownError(f"لطفاً {wait} ثانیه‌ی دیگر دوباره تلاش کنید.")

    # Any older unused code for this number becomes invalid.
    OTPCode.objects.filter(phone=phone, is_used=False).update(is_used=True)

    code = _generate_code()
    otp = OTPCode.objects.create(
        phone=phone,
        code_hash=_hash_code(phone, code),
        expires_at=now + timedelta(seconds=settings.OTP_TTL_SECONDS),
    )
    try:
        get_sms_backend().send_otp(phone, code)
    except SMSDeliveryError:
        logger.exception("SMS delivery failed for %s", phone)
        # The user never received this code: remove it so the cooldown
        # does not block an immediate retry.
        otp.delete()
        raise OTPDeliveryError("ارسال پیامک با خطا مواجه شد. لطفاً دوباره تلاش کنید.")
    return settings.OTP_TTL_SECONDS


def verify_otp(raw_phone, code):
    """Check a code. Marks it used on success. Raises OTPError on any failure."""
    phone = normalize_phone(raw_phone)
    otp = OTPCode.objects.filter(phone=phone, is_used=False).order_by("-created_at").first()
    if otp is None or otp.is_expired:
        raise OTPError("کد منقضی شده است. لطفاً کد جدید درخواست کنید.")
    if otp.attempts >= settings.OTP_MAX_ATTEMPTS:
        otp.is_used = True
        otp.save(update_fields=["is_used"])
        raise OTPError("تعداد تلاش‌ها بیش از حد مجاز است. لطفاً کد جدید درخواست کنید.")

    code = str(code).strip().translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
    if not hmac.compare_digest(otp.code_hash, _hash_code(phone, code)):
        otp.attempts += 1
        otp.save(update_fields=["attempts"])
        raise OTPError("کد وارد‌شده صحیح نیست.")

    otp.is_used = True
    otp.save(update_fields=["is_used"])
    return phone


@transaction.atomic
def login_with_phone(phone, current_user=None):
    """
    Return the account for a verified phone number, creating it if needed.

    If the request came from a guest session:
      - phone not registered yet  -> the guest account is upgraded in place
      - phone already registered  -> guest data is moved to that account and
                                     the guest account is deactivated
    """
    existing = User.objects.filter(phone=phone).first()
    guest = current_user if (current_user and current_user.is_authenticated and current_user.is_guest) else None

    if guest and existing is None:
        guest.phone = phone
        guest.is_guest = False
        guest.save(update_fields=["phone", "is_guest"])
        return guest, True

    if existing is None:
        return User.objects.create_user(phone=phone), True

    if not existing.is_active:
        raise OTPError("این حساب کاربری غیرفعال شده است.")

    if guest and guest.pk != existing.pk:
        guest_merged.send(sender=User, guest=guest, user=existing)
        guest.is_active = False
        guest.save(update_fields=["is_active"])

    return existing, False
