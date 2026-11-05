"""Cart, checkout, stock reservation and payment business logic."""
import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.catalog.models import ProductVariant

from .gateways import GatewayError, get_gateway
from .models import CartItem, Order, OrderItem, Payment

logger = logging.getLogger(__name__)


class OrderError(Exception):
    def __init__(self, message, code="order_error", status=400):
        super().__init__(message)
        self.code = code
        self.status = status


# ---------------------------------------------------------------------------
# Cart
# ---------------------------------------------------------------------------
def _check_variant(variant, quantity):
    if not (variant.is_active and variant.product.is_active and variant.product.category.is_active):
        raise OrderError("این کالا دیگر قابل خرید نیست.", code="unavailable")
    if quantity > settings.ORDER_MAX_QUANTITY_PER_ITEM:
        raise OrderError(f"حداکثر {settings.ORDER_MAX_QUANTITY_PER_ITEM} عدد از هر کالا قابل سفارش است.", code="max_quantity")
    if quantity > variant.stock:
        raise OrderError(f"موجودی این کالا {variant.stock} عدد است.", code="insufficient_stock")


def add_to_cart(user, variant, quantity):
    item = CartItem.objects.filter(user=user, variant=variant).first()
    new_quantity = (item.quantity if item else 0) + quantity
    _check_variant(variant, new_quantity)
    if item:
        item.quantity = new_quantity
        item.save(update_fields=["quantity"])
        return item
    return CartItem.objects.create(user=user, variant=variant, quantity=quantity)


def set_cart_quantity(item, quantity):
    _check_variant(item.variant, quantity)
    item.quantity = quantity
    item.save(update_fields=["quantity"])
    return item


def shipping_for(subtotal):
    free_over = settings.ORDER_FREE_SHIPPING_OVER
    if free_over and subtotal >= free_over:
        return 0
    return settings.ORDER_SHIPPING_COST if subtotal else 0


def cart_summary(user):
    items = list(
        CartItem.objects.filter(user=user).select_related("variant__product__category").order_by("added_at")
    )
    subtotal = sum(i.line_total for i in items)
    shipping = shipping_for(subtotal)
    return items, subtotal, shipping, subtotal + shipping


# ---------------------------------------------------------------------------
# Checkout
# ---------------------------------------------------------------------------
@transaction.atomic
def checkout(user, address, note=""):
    """
    Turn the cart into an order and reserve stock.

    Stock is deducted with a conditional UPDATE (stock >= quantity), so two
    customers can never buy the last item at the same time.
    """
    if user.is_guest:
        raise OrderError("برای ثبت سفارش، لطفاً با شماره موبایل وارد شوید.", code="login_required", status=403)
    if address.user_id != user.pk:
        raise OrderError("نشانی پیدا نشد.", code="address_not_found", status=404)

    # Lock only the cart rows (PostgreSQL refuses FOR UPDATE on the nullable
    # category join); stock itself is taken with a conditional UPDATE below.
    items = list(
        CartItem.objects.filter(user=user)
        .select_related("variant__product__category")
        .select_for_update(of=("self",))
    )
    if not items:
        raise OrderError("سبد خرید خالی است.", code="empty_cart")

    for item in items:
        _check_variant(item.variant, item.quantity)

    subtotal = sum(i.line_total for i in items)
    shipping = shipping_for(subtotal)
    order = Order.objects.create(
        user=user,
        recipient_name=address.recipient_name,
        recipient_phone=address.recipient_phone,
        province=address.province,
        city=address.city,
        address=address.address,
        postal_code=address.postal_code,
        note=note,
        subtotal=subtotal,
        shipping_cost=shipping,
        total=subtotal + shipping,
        reserved_until=timezone.now() + timedelta(minutes=settings.ORDER_PAYMENT_TIMEOUT_MINUTES),
    )
    for item in items:
        updated = ProductVariant.objects.filter(pk=item.variant_id, stock__gte=item.quantity).update(
            stock=F("stock") - item.quantity
        )
        if not updated:
            # Someone else bought it a moment ago; the whole transaction is rolled back.
            raise OrderError(f"موجودی «{item.variant.product.name}» کافی نیست.", code="insufficient_stock", status=409)
        OrderItem.objects.create(
            order=order,
            variant=item.variant,
            product_name=item.variant.product.name,
            variant_label=" / ".join(p for p in (item.variant.size, item.variant.color) if p),
            unit_price=item.variant.price,
            quantity=item.quantity,
        )
    CartItem.objects.filter(pk__in=[i.pk for i in items]).delete()
    return order


def _release_stock(order):
    for item in order.items.all():
        if item.variant_id:
            ProductVariant.objects.filter(pk=item.variant_id).update(stock=F("stock") + item.quantity)


@transaction.atomic
def cancel_order(order, new_status=Order.Status.CANCELLED):
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.status != Order.Status.PENDING_PAYMENT:
        raise OrderError("فقط سفارش‌های پرداخت‌نشده قابل لغو هستند.", code="not_cancellable")
    order.status = new_status
    order.save(update_fields=["status", "updated_at"])
    _release_stock(order)
    return order


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------
def start_payment(order, callback_url, request=None):
    if order.status != Order.Status.PENDING_PAYMENT:
        raise OrderError("این سفارش در انتظار پرداخت نیست.", code="not_payable")
    if order.reserved_until and order.reserved_until <= timezone.now():
        cancel_order(order, new_status=Order.Status.EXPIRED)
        raise OrderError("مهلت پرداخت این سفارش تمام شده است. لطفاً دوباره سفارش دهید.", code="expired")
    gateway = get_gateway()
    try:
        started = gateway.start(order, order.total, callback_url, request=request)
    except GatewayError:
        logger.exception("Payment start failed for order %s", order.number)
        raise OrderError("اتصال به درگاه پرداخت برقرار نشد. لطفاً دوباره تلاش کنید.", code="gateway_error", status=503)
    Payment.objects.create(order=order, gateway=gateway.name, amount=order.total, authority=started.authority, raw_response=started.raw)
    return started.payment_url


@transaction.atomic
def complete_payment(authority, callback_params):
    """
    Called when the bank redirects the customer back. Idempotent: refreshing
    the callback page or a duplicate redirect never double-processes an order.
    Returns (order, success).
    """
    payment = Payment.objects.select_for_update().select_related("order").filter(authority=authority).first()
    if payment is None:
        raise OrderError("تراکنش پیدا نشد.", code="payment_not_found", status=404)
    order = Order.objects.select_for_update().get(pk=payment.order_id)

    if payment.status == Payment.Status.SUCCEEDED:
        return order, True
    if payment.status == Payment.Status.FAILED:
        return order, False

    try:
        result = get_gateway().verify(payment, callback_params)
    except GatewayError:
        logger.exception("Payment verify failed for %s", authority)
        # Leave as 'initiated' so a later retry can still verify it.
        return order, False

    payment.raw_response = result.raw
    payment.verified_at = timezone.now()
    if not result.success:
        payment.status = Payment.Status.FAILED
        payment.save(update_fields=["status", "raw_response", "verified_at"])
        return order, False

    payment.status = Payment.Status.SUCCEEDED
    payment.ref_id = result.ref_id
    payment.card_pan = result.card_pan
    payment.save(update_fields=["status", "ref_id", "card_pan", "raw_response", "verified_at"])

    if order.status == Order.Status.PENDING_PAYMENT:
        order.status = Order.Status.PAID
        order.paid_at = timezone.now()
        order.save(update_fields=["status", "paid_at", "updated_at"])
    elif order.status in (Order.Status.EXPIRED, Order.Status.CANCELLED):
        # Money arrived after the reservation lapsed. Never silently lose a
        # paid order: take the stock again if possible, otherwise flag for staff.
        logger.error("Payment %s succeeded for %s order %s — needs staff review", authority, order.status, order.number)
        short = []
        for item in order.items.all():
            if not item.variant_id:
                short.append(item.product_name)
                continue
            taken = ProductVariant.objects.filter(pk=item.variant_id, stock__gte=item.quantity).update(
                stock=F("stock") - item.quantity
            )
            if not taken:
                short.append(item.product_name)
        flag = " | پرداخت پس از انقضای مهلت"
        if short:
            flag += " — موجودی کافی نیست: " + "، ".join(short) + " (تماس با مشتری یا استرداد وجه)"
        order.status = Order.Status.PAID
        order.paid_at = timezone.now()
        order.note = (order.note + flag)[:300]
        order.save(update_fields=["status", "paid_at", "note", "updated_at"])
    return order, True
