from unittest import mock

from django.test import override_settings

from apps.accounts.models import User
from apps.accounts.signals import guest_merged
from apps.catalog.testing import make_product
from apps.core.testing import APITestBase, EagerCeleryMixin, make_image
from apps.orders.models import Order
from apps.tryon.models import TryOnJob

from .backends import ExpoPushBackend, LocMemPushBackend, PushDeliveryError, PushMessage
from .models import PushDevice

LOCMEM = override_settings(PUSH_BACKEND="apps.notifications.backends.LocMemPushBackend")


@LOCMEM
class PushTestBase(EagerCeleryMixin, APITestBase):
    def setUp(self):
        super().setUp()
        LocMemPushBackend.outbox = []
        LocMemPushBackend.dead_tokens = set()
        self.user = User.objects.create_user(phone="09121234567")
        self.authenticate(self.user)

    def register(self, token="ExponentPushToken[abc]", platform="android"):
        return self.client.post("/api/v1/notifications/devices/", {"token": token, "platform": platform}, format="json")

    def make_order(self, **kwargs):
        defaults = dict(user=self.user, recipient_name="سارا", recipient_phone="09121234567", province="تهران",
                        city="تهران", address="خیابان ولیعصر", postal_code="1234567890", subtotal=1000, total=1000)
        return Order.objects.create(**{**defaults, **kwargs})


class DeviceRegistrationTests(PushTestBase):
    def test_register_is_idempotent_and_moves_token_to_current_user(self):
        self.assertEqual(self.register().status_code, 204)
        self.assertEqual(self.register().status_code, 204)
        self.assertEqual(PushDevice.objects.count(), 1)
        other = User.objects.create_user(phone="09351112233")
        self.authenticate(other)
        self.register()
        self.assertEqual(PushDevice.objects.get().user, other)

    def test_guests_can_register_and_devices_follow_the_merge(self):
        guest = User.objects.create_guest()
        self.authenticate(guest)
        self.register()
        guest_merged.send(sender=User, guest=guest, user=self.user)
        self.assertEqual(PushDevice.objects.get().user, self.user)

    def test_remove_on_logout(self):
        self.register()
        resp = self.client.delete("/api/v1/notifications/devices/", {"token": "ExponentPushToken[abc]"}, format="json")
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(PushDevice.objects.exists())

    def test_invalid_platform_and_anonymous_are_refused(self):
        self.assertEqual(self.register(platform="windows").status_code, 400)
        self.client.credentials()
        self.assertEqual(self.register().status_code, 401)


class TryOnPushTests(PushTestBase):
    def test_completed_tryon_sends_one_push(self):
        self.register()
        product = make_product()
        photo = self.client.post("/api/v1/tryon/photos/", {"image": make_image()}, format="multipart").data["id"]
        with self.captureOnCommitCallbacks(execute=True):
            job = self.client.post("/api/v1/tryon/jobs/", {"product_id": product.pk, "photo_id": photo}, format="json")
        self.assertEqual(TryOnJob.objects.get(pk=job.data["id"]).status, "completed")
        self.assertEqual(len(LocMemPushBackend.outbox), 1)
        message = LocMemPushBackend.outbox[0]
        self.assertEqual(message.title, "پرو مجازی آماده شد")
        self.assertEqual(message.data, {"type": "tryon", "job_id": job.data["id"]})

        # The same request again is answered from the cache: no push, the customer is looking at it.
        with self.captureOnCommitCallbacks(execute=True):
            again = self.client.post("/api/v1/tryon/jobs/", {"product_id": product.pk, "photo_id": photo}, format="json")
        self.assertEqual(again.status_code, 200)
        self.assertEqual(len(LocMemPushBackend.outbox), 1)

    def test_no_devices_no_push(self):
        product = make_product()
        photo = self.client.post("/api/v1/tryon/photos/", {"image": make_image()}, format="multipart").data["id"]
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post("/api/v1/tryon/jobs/", {"product_id": product.pk, "photo_id": photo}, format="json")
        self.assertEqual(LocMemPushBackend.outbox, [])


class OrderPushTests(PushTestBase):
    def test_status_changes_notify_once_each(self):
        self.register()
        order = self.make_order()
        with self.captureOnCommitCallbacks(execute=True):
            order.status = Order.Status.PAID  # paid: the customer just saw the receipt, no push
            order.save()
        self.assertEqual(LocMemPushBackend.outbox, [])

        order = Order.objects.get(pk=order.pk)  # as the admin form would load it
        with self.captureOnCommitCallbacks(execute=True):
            order.status = Order.Status.SHIPPED
            order.tracking_code = "TR-998"
            order.save()
            order.save()  # saving again without a change does not notify twice
        self.assertEqual(len(LocMemPushBackend.outbox), 1)
        message = LocMemPushBackend.outbox[0]
        self.assertEqual(message.title, "سفارش شما ارسال شد")
        self.assertIn("TR-998", message.body)
        self.assertEqual(message.data, {"type": "order", "order_number": order.number})

    def test_dead_tokens_are_deactivated(self):
        self.register("dead-token")
        self.register("live-token", "ios")
        LocMemPushBackend.dead_tokens = {"dead-token"}
        order = self.make_order(status=Order.Status.PAID)
        with self.captureOnCommitCallbacks(execute=True):
            order.status = Order.Status.DELIVERED
            order.save()
        self.assertEqual(len(LocMemPushBackend.outbox), 2)
        self.assertFalse(PushDevice.objects.get(token="dead-token").is_active)
        self.assertTrue(PushDevice.objects.get(token="live-token").is_active)


class ExpoBackendTests(APITestBase):
    def test_sends_batches_and_reports_unregistered_devices(self):
        response = mock.Mock(status_code=200)
        response.json.return_value = {"data": [
            {"status": "ok", "id": "1"},
            {"status": "error", "message": "gone", "details": {"error": "DeviceNotRegistered"}},
        ]}
        with mock.patch("apps.notifications.backends.requests.post", return_value=response) as post:
            dead = ExpoPushBackend().send([PushMessage("a", "t", "b"), PushMessage("b", "t", "b", {"x": 1})])
        self.assertEqual(dead, ["b"])
        payload = post.call_args.kwargs["json"]
        self.assertEqual([p["to"] for p in payload], ["a", "b"])
        self.assertEqual(payload[1]["data"], {"x": 1})

    def test_http_error_raises(self):
        with mock.patch("apps.notifications.backends.requests.post", return_value=mock.Mock(status_code=500, text="x")):
            with self.assertRaises(PushDeliveryError):
                ExpoPushBackend().send([PushMessage("a", "t", "b")])
