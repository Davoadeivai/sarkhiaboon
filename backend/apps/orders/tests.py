from datetime import timedelta
from unittest import mock
from urllib.parse import parse_qs, urlparse

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.signals import guest_merged
from apps.catalog.models import ProductVariant
from apps.catalog.testing import make_product
from apps.core.testing import APITestBase

from . import services, tasks
from .gateways import GatewayError, ZarinpalGateway
from .models import Address, CartItem, Order, Payment


class OrderTestBase(APITestBase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(phone="09121234567")
        self.authenticate(self.user)
        self.product = make_product(price=400_000, stock=3, sizes=("M", "L"))
        self.variant = self.product.variants.get(size="M")
        self.address = Address.objects.create(
            user=self.user, recipient_name="سارا محمدی", recipient_phone="09121234567",
            province="تهران", city="تهران", address="خیابان ولیعصر، پلاک ۱", postal_code="1234567890",
        )

    def add(self, variant=None, quantity=1):
        return self.client.post("/api/v1/orders/cart/items/", {"variant_id": (variant or self.variant).pk, "quantity": quantity}, format="json")

    def checkout(self):
        return self.client.post("/api/v1/orders/checkout/", {"address_id": self.address.pk}, format="json")

    def stock(self, variant=None):
        return ProductVariant.objects.get(pk=(variant or self.variant).pk).stock


class CartTests(OrderTestBase):
    def test_add_merge_update_remove(self):
        resp = self.add(quantity=1)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["subtotal"], 400_000)
        resp = self.add(quantity=1)  # same variant: quantities combine
        self.assertEqual(len(resp.data["items"]), 1)
        self.assertEqual(resp.data["items"][0]["quantity"], 2)
        item_id = resp.data["items"][0]["id"]
        resp = self.client.patch(f"/api/v1/orders/cart/items/{item_id}/", {"quantity": 3}, format="json")
        self.assertEqual(resp.data["total"], 1_200_000)
        resp = self.client.delete(f"/api/v1/orders/cart/items/{item_id}/")
        self.assertEqual(resp.data["items"], [])

    def test_cannot_exceed_stock_or_limit(self):
        resp = self.add(quantity=4)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["code"], "insufficient_stock")
        with override_settings(ORDER_MAX_QUANTITY_PER_ITEM=2):
            self.assertEqual(self.add(quantity=3).data["code"], "max_quantity")

    def test_inactive_product_cannot_be_added(self):
        self.product.is_active = False
        self.product.save()
        self.assertEqual(self.add().data["code"], "unavailable")

    @override_settings(ORDER_SHIPPING_COST=50_000, ORDER_FREE_SHIPPING_OVER=1_000_000)
    def test_shipping_and_free_shipping(self):
        self.assertEqual(self.add().data["shipping_cost"], 50_000)
        self.assertEqual(self.add(quantity=2).data["shipping_cost"], 0)  # 1.2M >= 1M

    def test_carts_are_private(self):
        item_id = self.add().data["items"][0]["id"]
        self.authenticate(User.objects.create_user(phone="09350000000"))
        self.assertEqual(self.client.get("/api/v1/orders/cart/").data["items"], [])
        self.assertEqual(self.client.delete(f"/api/v1/orders/cart/items/{item_id}/").status_code, 404)

    def test_guest_cart_merges_into_account(self):
        guest = User.objects.create_guest()
        other = self.product.variants.get(size="L")
        CartItem.objects.create(user=guest, variant=self.variant, quantity=2)
        CartItem.objects.create(user=guest, variant=other, quantity=1)
        CartItem.objects.create(user=self.user, variant=self.variant, quantity=2)
        guest_merged.send(sender=User, guest=guest, user=self.user)
        quantities = dict(CartItem.objects.filter(user=self.user).values_list("variant__size", "quantity"))
        self.assertEqual(quantities, {"M": 3, "L": 1})  # 2+2 capped at stock 3
        self.assertFalse(CartItem.objects.filter(user=guest).exists())


class AddressTests(OrderTestBase):
    def test_create_normalizes_and_keeps_single_default(self):
        resp = self.client.post("/api/v1/orders/addresses/", {
            "title": "محل کار", "recipient_name": "سارا", "recipient_phone": "+989121112233",
            "province": "تهران", "city": "تهران", "address": "خیابان آزادی", "postal_code": "۱۱۱۱۱-۲۲۲۲۲", "is_default": True,
        }, format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["recipient_phone"], "09121112233")
        self.assertEqual(resp.data["postal_code"], "1111122222")
        self.assertEqual(Address.objects.filter(user=self.user, is_default=True).count(), 1)

    def test_first_address_becomes_default(self):
        Address.objects.all().delete()
        resp = self.client.post("/api/v1/orders/addresses/", {
            "recipient_name": "علی", "recipient_phone": "09121112233", "province": "فارس",
            "city": "شیراز", "address": "زند", "postal_code": "7111111111",
        }, format="json")
        self.assertTrue(resp.data["is_default"])

    def test_invalid_postal_code(self):
        resp = self.client.post("/api/v1/orders/addresses/", {
            "recipient_name": "علی", "recipient_phone": "09121112233", "province": "فارس",
            "city": "شیراز", "address": "زند", "postal_code": "123",
        }, format="json")
        self.assertEqual(resp.status_code, 400)


class CheckoutTests(OrderTestBase):
    def test_checkout_reserves_stock_and_snapshots(self):
        self.add(quantity=2)
        resp = self.checkout()
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["status"], "pending_payment")
        self.assertEqual(resp.data["total"], 800_000)
        self.assertTrue(resp.data["number"].startswith("SK"))
        self.assertEqual(self.stock(), 1)
        self.assertFalse(CartItem.objects.filter(user=self.user).exists())
        # Later price change does not alter the order
        self.product.price = 999_000
        self.product.save()
        order = self.client.get(f"/api/v1/orders/{resp.data['number']}/").data
        self.assertEqual(order["items"][0]["unit_price"], 400_000)
        self.assertEqual(order["items"][0]["variant_label"], "M / سفید")

    def test_empty_cart(self):
        self.assertEqual(self.checkout().data["code"], "empty_cart")

    def test_guest_must_register_to_checkout(self):
        guest = User.objects.create_guest()
        self.authenticate(guest)
        CartItem.objects.create(user=guest, variant=self.variant, quantity=1)
        address = Address.objects.create(user=guest, recipient_name="x", recipient_phone="09121112233",
                                         province="x", city="x", address="x", postal_code="1234567890")
        resp = self.client.post("/api/v1/orders/checkout/", {"address_id": address.pk}, format="json")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.data["code"], "login_required")

    def test_cannot_use_another_users_address(self):
        other = User.objects.create_user(phone="09350000000")
        foreign = Address.objects.create(user=other, recipient_name="x", recipient_phone="09121112233",
                                         province="x", city="x", address="x", postal_code="1234567890")
        self.add()
        resp = self.client.post("/api/v1/orders/checkout/", {"address_id": foreign.pk}, format="json")
        self.assertEqual(resp.status_code, 404)

    def test_last_item_race_rolls_back_whole_order(self):
        """Stock changed between adding to cart and checkout (someone else bought it)."""
        second = make_product("شلوار", price=100_000, stock=2)
        self.add(quantity=2)
        self.add(variant=second.variants.first(), quantity=1)
        ProductVariant.objects.filter(pk=self.variant.pk).update(stock=1)
        resp = self.checkout()
        self.assertEqual(resp.data["code"], "insufficient_stock")
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(self.stock(second.variants.first()), 2)  # nothing was deducted
        self.assertEqual(CartItem.objects.filter(user=self.user).count(), 2)  # cart kept

    def test_conditional_stock_update_blocks_oversell(self):
        """Even if validation passed, the guarded UPDATE refuses to go below zero."""
        self.add(quantity=2)
        with mock.patch.object(services, "_check_variant"):
            ProductVariant.objects.filter(pk=self.variant.pk).update(stock=1)
            resp = self.checkout()
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(self.stock(), 1)
        self.assertEqual(Order.objects.count(), 0)

    def test_cancel_releases_stock(self):
        self.add(quantity=2)
        number = self.checkout().data["number"]
        resp = self.client.post(f"/api/v1/orders/{number}/cancel/")
        self.assertEqual(resp.data["status"], "cancelled")
        self.assertEqual(self.stock(), 3)
        self.assertEqual(self.client.post(f"/api/v1/orders/{number}/cancel/").data["code"], "not_cancellable")

    def test_unpaid_orders_expire_and_release_stock(self):
        self.add(quantity=2)
        number = self.checkout().data["number"]
        Order.objects.filter(number=number).update(reserved_until=timezone.now() - timedelta(minutes=1))
        self.assertEqual(tasks.release_unpaid_orders(), 1)
        self.assertEqual(Order.objects.get(number=number).status, "expired")
        self.assertEqual(self.stock(), 3)

    def test_orders_are_private(self):
        self.add()
        number = self.checkout().data["number"]
        self.authenticate(User.objects.create_user(phone="09350000000"))
        self.assertEqual(self.client.get(f"/api/v1/orders/{number}/").status_code, 404)
        self.assertEqual(self.client.get("/api/v1/orders/").data["count"], 0)


class PaymentFlowTests(OrderTestBase):
    """Full round trip with the sandbox gateway: pay -> bank page -> callback -> app deep link."""

    def _order(self, quantity=1):
        self.add(quantity=quantity)
        return self.checkout().data["number"]

    def _pay_and_return(self, number, bank_status):
        pay = self.client.post(f"/api/v1/orders/{number}/pay/")
        self.assertEqual(pay.status_code, 200, pay.data)
        bank_page = self.client.get(urlparse(pay.data["payment_url"]).path)
        self.assertEqual(bank_page.status_code, 200)
        authority = Payment.objects.filter(order__number=number).order_by("-id").first().authority
        self.client.credentials()  # the bank redirect carries no token
        callback = self.client.get("/api/v1/orders/payment/callback/", {"Authority": authority, "Status": bank_status})
        self.authenticate(self.user)
        return callback

    def test_successful_payment(self):
        number = self._order()
        callback = self._pay_and_return(number, "OK")
        self.assertEqual(callback.status_code, 302)
        target = urlparse(callback["Location"])
        self.assertEqual(target.scheme, "sarkhiaboon")  # back into the app
        self.assertEqual(parse_qs(target.query), {"order": [number], "status": ["success"]})
        order = Order.objects.get(number=number)
        self.assertEqual(order.status, "paid")
        self.assertIsNotNone(order.paid_at)
        payment = order.payments.get()
        self.assertEqual(payment.status, "succeeded")
        self.assertTrue(payment.ref_id)
        self.assertEqual(self.stock(), 2)

    def test_failed_payment_keeps_order_payable(self):
        number = self._order()
        callback = self._pay_and_return(number, "NOK")
        self.assertIn("status=failed", callback["Location"])
        self.assertEqual(Order.objects.get(number=number).status, "pending_payment")
        # Customer can try again
        self.assertEqual(self._pay_and_return(number, "OK").status_code, 302)
        self.assertEqual(Order.objects.get(number=number).status, "paid")

    def test_callback_is_idempotent(self):
        number = self._order()
        self._pay_and_return(number, "OK")
        authority = Payment.objects.get(order__number=number).authority
        with mock.patch("apps.orders.gateways.SandboxGateway.verify") as verify:
            again = self.client.get("/api/v1/orders/payment/callback/", {"Authority": authority, "Status": "OK"})
            verify.assert_not_called()  # already verified: no second bank call
        self.assertIn("status=success", again["Location"])
        self.assertEqual(self.stock(), 2)  # stock not deducted twice

    def test_unknown_authority(self):
        resp = self.client.get("/api/v1/orders/payment/callback/", {"Authority": "FAKE", "Status": "OK"})
        self.assertIn("status=failed", resp["Location"])

    def test_paid_order_cannot_be_paid_or_cancelled_again(self):
        number = self._order()
        self._pay_and_return(number, "OK")
        self.assertEqual(self.client.post(f"/api/v1/orders/{number}/pay/").data["code"], "not_payable")
        self.assertEqual(self.client.post(f"/api/v1/orders/{number}/cancel/").data["code"], "not_cancellable")

    def test_expired_order_cannot_start_payment(self):
        number = self._order()
        Order.objects.filter(number=number).update(reserved_until=timezone.now() - timedelta(minutes=1))
        resp = self.client.post(f"/api/v1/orders/{number}/pay/")
        self.assertEqual(resp.data["code"], "expired")
        self.assertEqual(self.stock(), 3)

    def test_late_payment_after_expiry_is_not_lost(self):
        number = self._order()
        self.client.post(f"/api/v1/orders/{number}/pay/")
        order = Order.objects.get(number=number)
        services.cancel_order(order, new_status=Order.Status.EXPIRED)  # deadline passed while at the bank
        self.assertEqual(self.stock(), 3)
        authority = Payment.objects.get(order=order).authority
        self.client.get("/api/v1/orders/payment/callback/", {"Authority": authority, "Status": "OK"})
        order.refresh_from_db()
        self.assertEqual(order.status, "paid")
        self.assertIn("پرداخت پس از انقضای مهلت", order.note)
        self.assertEqual(self.stock(), 2)  # stock taken again

    def test_late_payment_without_stock_is_flagged(self):
        number = self._order()
        self.client.post(f"/api/v1/orders/{number}/pay/")
        order = Order.objects.get(number=number)
        services.cancel_order(order, new_status=Order.Status.EXPIRED)
        ProductVariant.objects.filter(pk=self.variant.pk).update(stock=0)  # sold to someone else
        authority = Payment.objects.get(order=order).authority
        self.client.get("/api/v1/orders/payment/callback/", {"Authority": authority, "Status": "OK"})
        order.refresh_from_db()
        self.assertEqual(order.status, "paid")
        self.assertIn("موجودی کافی نیست", order.note)
        self.assertEqual(self.stock(), 0)  # never negative

    def test_gateway_down(self):
        number = self._order()
        with mock.patch("apps.orders.gateways.SandboxGateway.start", side_effect=GatewayError("down")):
            resp = self.client.post(f"/api/v1/orders/{number}/pay/")
        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.data["code"], "gateway_error")

    def test_sandbox_page_disabled_for_real_gateway(self):
        with override_settings(PAYMENT_GATEWAY="apps.orders.gateways.ZarinpalGateway"):
            self.assertEqual(self.client.get("/api/v1/orders/payment/sandbox/ABC/").status_code, 404)


class FakeZarinpalSession:
    def __init__(self, *payloads):
        self.payloads, self.calls = list(payloads), []

    def post(self, url, json=None, **kwargs):
        self.calls.append((url, json))
        payload = self.payloads.pop(0)
        return mock.Mock(json=mock.Mock(return_value=payload))


@override_settings(ZARINPAL_MERCHANT_ID="merchant-uuid", ZARINPAL_SANDBOX=True)
class ZarinpalGatewayTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone="09121234567")
        self.order = Order.objects.create(
            user=self.user, recipient_name="x", recipient_phone="09121234567", province="x", city="x",
            address="x", postal_code="1234567890", subtotal=250_000, total=250_000,
        )

    def test_start_sends_rial_and_builds_startpay_url(self):
        session = FakeZarinpalSession({"data": {"code": 100, "authority": "A000123"}, "errors": []})
        started = ZarinpalGateway(session=session).start(self.order, 250_000, "https://api.x/cb/")
        url, body = session.calls[0]
        self.assertEqual(url, "https://sandbox.zarinpal.com/pg/v4/payment/request.json")
        self.assertEqual(body["amount"], 2_500_000)  # Toman -> Rial
        self.assertEqual(body["merchant_id"], "merchant-uuid")
        self.assertEqual(started.payment_url, "https://sandbox.zarinpal.com/pg/StartPay/A000123")

    def test_start_refused(self):
        session = FakeZarinpalSession({"data": [], "errors": {"code": -9, "message": "validation"}})
        with self.assertRaises(GatewayError):
            ZarinpalGateway(session=session).start(self.order, 250_000, "https://api.x/cb/")

    def test_verify_uses_stored_amount(self):
        payment = Payment.objects.create(order=self.order, gateway="zarinpal", amount=250_000, authority="A000123")
        session = FakeZarinpalSession({"data": {"code": 100, "ref_id": 987654, "card_pan": "502229******5995"}, "errors": []})
        result = ZarinpalGateway(session=session).verify(payment, {"Status": "OK", "Authority": "A000123", "amount": "1"})
        self.assertTrue(result.success)
        self.assertEqual(result.ref_id, "987654")
        self.assertEqual(session.calls[0][1]["amount"], 2_500_000)  # ignores any amount in the callback

    def test_verify_already_verified_counts_as_success(self):
        payment = Payment.objects.create(order=self.order, gateway="zarinpal", amount=250_000, authority="A1")
        session = FakeZarinpalSession({"data": {"code": 101, "ref_id": 1}, "errors": []})
        self.assertTrue(ZarinpalGateway(session=session).verify(payment, {"Status": "OK"}).success)

    def test_verify_cancelled_by_customer_makes_no_call(self):
        payment = Payment.objects.create(order=self.order, gateway="zarinpal", amount=250_000, authority="A2")
        session = FakeZarinpalSession()
        self.assertFalse(ZarinpalGateway(session=session).verify(payment, {"Status": "NOK"}).success)
        self.assertEqual(session.calls, [])

    def test_missing_merchant_id(self):
        with override_settings(ZARINPAL_MERCHANT_ID=""):
            with self.assertRaises(GatewayError):
                ZarinpalGateway(session=FakeZarinpalSession()).start(self.order, 1, "https://x/")


class OrderAdminSmokeTests(OrderTestBase):
    def test_admin_pages_render(self):
        self.add()
        number = self.checkout().data["number"]
        admin = User.objects.create_superuser(phone="09120000000", password="pass-1234")
        self.client.credentials()
        self.client.force_login(admin)
        order = Order.objects.get(number=number)
        for url in ("/admin/orders/order/", f"/admin/orders/order/{order.pk}/change/", "/admin/orders/payment/",
                    "/admin/orders/address/", "/admin/orders/cartitem/"):
            self.assertEqual(self.client.get(url).status_code, 200, url)
