from datetime import timedelta
from unittest import mock

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from apps.core.testing import APITestBase
from django.utils import timezone

from .models import OTPCode, User
from .phone import normalize_phone
from .signals import guest_merged
from .sms import LocMemSMSBackend

TEST_SETTINGS = dict(
    SMS_BACKEND="apps.accounts.sms.LocMemSMSBackend",
    OTP_RESEND_COOLDOWN_SECONDS=60,
    OTP_MAX_ATTEMPTS=3,
)


class PhoneNormalizationTests(TestCase):
    def test_accepted_formats(self):
        for raw in ("09121234567", "+989121234567", "00989121234567", "989121234567", "9121234567",
                    "۰۹۱۲۱۲۳۴۵۶۷", "0912 123 4567", "0912-123-4567"):
            self.assertEqual(normalize_phone(raw), "09121234567", raw)

    def test_rejected_formats(self):
        for raw in ("", "0912123456", "08121234567", "abc", "091212345678"):
            with self.assertRaises(ValidationError):
                normalize_phone(raw)


@override_settings(**TEST_SETTINGS)
class OTPLoginFlowTests(APITestBase):
    def setUp(self):
        super().setUp()
        LocMemSMSBackend.outbox.clear()

    def _request(self, phone="09121234567"):
        return self.client.post("/api/v1/auth/otp/request/", {"phone": phone}, format="json")

    def _last_code(self):
        return LocMemSMSBackend.outbox[-1]["code"]

    def test_full_login_creates_user_and_returns_tokens(self):
        self.assertEqual(self._request().status_code, 200)
        code = self._last_code()
        resp = self.client.post("/api/v1/auth/otp/verify/", {"phone": "09121234567", "code": code}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)
        self.assertTrue(resp.data["is_new_user"])
        self.assertTrue(User.objects.filter(phone="09121234567").exists())

        # Token works on a protected endpoint
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
        me = self.client.get("/api/v1/auth/me/")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["phone"], "09121234567")

    def test_code_is_stored_hashed(self):
        self._request()
        otp = OTPCode.objects.get()
        self.assertNotEqual(otp.code_hash, self._last_code())
        self.assertEqual(len(otp.code_hash), 64)

    def test_second_login_is_not_new_user(self):
        User.objects.create_user(phone="09121234567")
        self._request()
        resp = self.client.post("/api/v1/auth/otp/verify/", {"phone": "09121234567", "code": self._last_code()}, format="json")
        self.assertFalse(resp.data["is_new_user"])

    def test_resend_cooldown(self):
        self.assertEqual(self._request().status_code, 200)
        self.assertEqual(self._request().status_code, 429)

    def test_wrong_code_then_lockout(self):
        self._request()
        for _ in range(3):
            resp = self.client.post("/api/v1/auth/otp/verify/", {"phone": "09121234567", "code": "00000"}, format="json")
            self.assertEqual(resp.status_code, 400)
        # Even the right code is refused after too many attempts
        resp = self.client.post("/api/v1/auth/otp/verify/", {"phone": "09121234567", "code": self._last_code()}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_code_cannot_be_reused(self):
        self._request()
        code = self._last_code()
        ok = self.client.post("/api/v1/auth/otp/verify/", {"phone": "09121234567", "code": code}, format="json")
        self.assertEqual(ok.status_code, 200)
        again = self.client.post("/api/v1/auth/otp/verify/", {"phone": "09121234567", "code": code}, format="json")
        self.assertEqual(again.status_code, 400)

    def test_expired_code(self):
        self._request()
        OTPCode.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        resp = self.client.post("/api/v1/auth/otp/verify/", {"phone": "09121234567", "code": self._last_code()}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_invalid_phone_rejected(self):
        self.assertEqual(self._request("12345").status_code, 400)

    def test_persian_digits_accepted_end_to_end(self):
        self.assertEqual(self._request("۰۹۱۲۱۲۳۴۵۶۷").status_code, 200)
        code = self._last_code().translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
        resp = self.client.post("/api/v1/auth/otp/verify/", {"phone": "۰۹۱۲۱۲۳۴۵۶۷", "code": code}, format="json")
        self.assertEqual(resp.status_code, 200)

    def test_sms_failure_returns_503(self):
        from .sms import SMSDeliveryError
        with mock.patch.object(LocMemSMSBackend, "send_otp", side_effect=SMSDeliveryError("down")):
            self.assertEqual(self._request().status_code, 503)
        # A failed send must not trigger the resend cooldown
        self.assertEqual(self._request().status_code, 200)


@override_settings(**TEST_SETTINGS)
class GuestFlowTests(APITestBase):
    def setUp(self):
        super().setUp()
        LocMemSMSBackend.outbox.clear()

    def _guest(self):
        resp = self.client.post("/api/v1/auth/guest/")
        self.assertEqual(resp.status_code, 201)
        return resp.data

    def _verify_as(self, access, phone="09121234567"):
        self.client.post("/api/v1/auth/otp/request/", {"phone": phone}, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        resp = self.client.post("/api/v1/auth/otp/verify/", {"phone": phone, "code": LocMemSMSBackend.outbox[-1]["code"]}, format="json")
        self.client.credentials()
        return resp

    def test_guest_is_upgraded_when_phone_is_new(self):
        guest = self._guest()
        self.assertTrue(guest["user"]["is_guest"])
        resp = self._verify_as(guest["access"])
        self.assertEqual(resp.data["user"]["id"], guest["user"]["id"])
        self.assertFalse(resp.data["user"]["is_guest"])

    def test_guest_merges_into_existing_account(self):
        existing = User.objects.create_user(phone="09121234567")
        guest = self._guest()
        received = []
        handler = lambda sender, guest, user, **kw: received.append((guest.pk, user.pk))
        guest_merged.connect(handler)
        try:
            resp = self._verify_as(guest["access"])
        finally:
            guest_merged.disconnect(handler)
        self.assertEqual(resp.data["user"]["id"], existing.pk)
        self.assertEqual(received, [(guest["user"]["id"], existing.pk)])
        self.assertFalse(User.objects.get(pk=guest["user"]["id"]).is_active)

    def test_stale_token_does_not_block_login(self):
        self.client.post("/api/v1/auth/otp/request/", {"phone": "09121234567"}, format="json")
        self.client.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")
        resp = self.client.post("/api/v1/auth/otp/verify/", {"phone": "09121234567", "code": LocMemSMSBackend.outbox[-1]["code"]}, format="json")
        self.assertEqual(resp.status_code, 200)

    def test_profile_update(self):
        guest = self._guest()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {guest['access']}")
        resp = self.client.patch("/api/v1/auth/me/", {"first_name": "سارا", "phone": "09999999999"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["first_name"], "سارا")
        self.assertIsNone(resp.data["phone"])  # phone is read-only; only OTP can set it

    def test_protected_endpoint_requires_auth(self):
        self.assertEqual(self.client.get("/api/v1/auth/me/").status_code, 401)
