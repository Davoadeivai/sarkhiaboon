import secrets

from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models

from apps.accounts.phone import validate_phone
from apps.catalog.models import ProductVariant
from apps.core.models import TimeStampedModel

postal_code_validator = RegexValidator(r"^\d{10}$", "کد پستی باید ۱۰ رقم باشد.")


class CartItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart_items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="+")
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "آیتم سبد خرید"
        verbose_name_plural = "سبدهای خرید"
        ordering = ("added_at",)
        constraints = [models.UniqueConstraint(fields=("user", "variant"), name="unique_cart_variant")]

    @property
    def line_total(self):
        return self.variant.price * self.quantity


class Address(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="addresses")
    title = models.CharField("عنوان", max_length=50, blank=True, help_text="مثلاً: خانه، محل کار")
    recipient_name = models.CharField("نام گیرنده", max_length=100)
    recipient_phone = models.CharField("موبایل گیرنده", max_length=11, validators=[validate_phone])
    province = models.CharField("استان", max_length=50)
    city = models.CharField("شهر", max_length=50)
    address = models.TextField("نشانی")
    postal_code = models.CharField("کد پستی", max_length=10, validators=[postal_code_validator])
    is_default = models.BooleanField("پیش‌فرض", default=False)

    class Meta:
        verbose_name = "نشانی"
        verbose_name_plural = "نشانی‌ها"
        ordering = ("-is_default", "-created_at")

    def __str__(self):
        return f"{self.recipient_name} — {self.city}"


def _order_number():
    return "SK" + "".join(secrets.choice("0123456789") for _ in range(8))


class Order(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", "در انتظار پرداخت"
        PAID = "paid", "پرداخت‌شده"
        PROCESSING = "processing", "در حال آماده‌سازی"
        SHIPPED = "shipped", "ارسال‌شده"
        DELIVERED = "delivered", "تحویل‌شده"
        CANCELLED = "cancelled", "لغوشده"
        EXPIRED = "expired", "منقضی (پرداخت نشد)"

    number = models.CharField("شماره سفارش", max_length=12, unique=True, default=_order_number, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField("وضعیت", max_length=20, choices=Status.choices, default=Status.PENDING_PAYMENT, db_index=True)

    # Shipping snapshot: stays correct even if the customer later edits or deletes the address
    recipient_name = models.CharField("نام گیرنده", max_length=100)
    recipient_phone = models.CharField("موبایل گیرنده", max_length=11)
    province = models.CharField("استان", max_length=50)
    city = models.CharField("شهر", max_length=50)
    address = models.TextField("نشانی")
    postal_code = models.CharField("کد پستی", max_length=10)
    note = models.CharField("توضیحات مشتری", max_length=300, blank=True)

    subtotal = models.PositiveBigIntegerField("جمع کالاها (تومان)")
    shipping_cost = models.PositiveBigIntegerField("هزینه‌ی ارسال (تومان)", default=0)
    total = models.PositiveBigIntegerField("مبلغ قابل پرداخت (تومان)")

    reserved_until = models.DateTimeField("مهلت پرداخت", null=True, blank=True)
    paid_at = models.DateTimeField("زمان پرداخت", null=True, blank=True)
    tracking_code = models.CharField("کد رهگیری مرسوله", max_length=50, blank=True)

    class Meta:
        verbose_name = "سفارش"
        verbose_name_plural = "سفارش‌ها"
        ordering = ("-created_at",)

    def __str__(self):
        return self.number

    @property
    def stock_is_reserved(self):
        """Stock stays deducted for pending, paid and later states; released when cancelled/expired."""
        return self.status not in (self.Status.CANCELLED, self.Status.EXPIRED)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(ProductVariant, null=True, on_delete=models.SET_NULL, related_name="+")
    # Snapshot at purchase time: invoices stay correct after price or name changes
    product_name = models.CharField("نام کالا", max_length=200)
    variant_label = models.CharField("سایز/رنگ", max_length=80, blank=True)
    unit_price = models.PositiveBigIntegerField("قیمت واحد (تومان)")
    quantity = models.PositiveIntegerField("تعداد")

    class Meta:
        verbose_name = "قلم سفارش"
        verbose_name_plural = "اقلام سفارش"

    @property
    def line_total(self):
        return self.unit_price * self.quantity


class Payment(models.Model):
    class Status(models.TextChoices):
        INITIATED = "initiated", "ارسال به درگاه"
        SUCCEEDED = "succeeded", "موفق"
        FAILED = "failed", "ناموفق"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payments")
    gateway = models.CharField("درگاه", max_length=30)
    amount = models.PositiveBigIntegerField("مبلغ (تومان)")
    authority = models.CharField("شناسه‌ی تراکنش درگاه", max_length=100, unique=True)
    status = models.CharField("وضعیت", max_length=12, choices=Status.choices, default=Status.INITIATED)
    ref_id = models.CharField("کد پیگیری بانکی", max_length=100, blank=True)
    card_pan = models.CharField("کارت (بخشی)", max_length=20, blank=True)
    raw_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "پرداخت"
        verbose_name_plural = "پرداخت‌ها"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.order.number} — {self.get_status_display()}"
