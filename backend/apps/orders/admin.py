from django.contrib import admin

from .models import Address, CartItem, Order, OrderItem, Payment


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    fields = ("product_name", "variant_label", "unit_price", "quantity")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    can_delete = False
    fields = ("gateway", "amount", "status", "ref_id", "card_pan", "created_at", "verified_at")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("number", "recipient_name", "city", "total", "status", "created_at", "paid_at")
    list_filter = ("status", "province")
    search_fields = ("number", "recipient_name", "recipient_phone", "user__phone", "tracking_code")
    date_hierarchy = "created_at"
    inlines = (OrderItemInline, PaymentInline)
    readonly_fields = ("number", "user", "subtotal", "shipping_cost", "total", "reserved_until", "paid_at", "created_at")
    fieldsets = (
        (None, {"fields": ("number", "user", "status", "tracking_code")}),
        ("ارسال", {"fields": ("recipient_name", "recipient_phone", "province", "city", "address", "postal_code", "note")}),
        ("مبالغ (تومان)", {"fields": ("subtotal", "shipping_cost", "total")}),
        ("زمان‌ها", {"fields": ("created_at", "reserved_until", "paid_at")}),
    )

    def has_add_permission(self, request):
        return False  # orders are only created by customers through checkout


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("order", "gateway", "amount", "status", "ref_id", "created_at")
    list_filter = ("status", "gateway")
    search_fields = ("order__number", "authority", "ref_id")
    readonly_fields = [f.name for f in Payment._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("recipient_name", "user", "province", "city", "is_default")
    search_fields = ("recipient_name", "recipient_phone", "user__phone", "postal_code")


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("user", "variant", "quantity", "added_at")
    search_fields = ("user__phone",)
