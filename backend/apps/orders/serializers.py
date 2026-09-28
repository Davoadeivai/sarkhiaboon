from rest_framework import serializers

from apps.accounts.serializers import PhoneField
from apps.catalog.models import ProductVariant
from apps.core.fields import MediaURLField

from .models import Address, CartItem, Order, OrderItem


class CartVariantSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source="product.id", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_slug = serializers.CharField(source="product.slug", read_only=True)
    image = MediaURLField(source="product.image", read_only=True)
    price = serializers.IntegerField(read_only=True)

    class Meta:
        model = ProductVariant
        fields = ("id", "product_id", "product_name", "product_slug", "image", "size", "color", "price", "stock")


class CartItemSerializer(serializers.ModelSerializer):
    variant = CartVariantSerializer(read_only=True)
    line_total = serializers.IntegerField(read_only=True)

    class Meta:
        model = CartItem
        fields = ("id", "variant", "quantity", "line_total")


class CartAddSerializer(serializers.Serializer):
    variant_id = serializers.PrimaryKeyRelatedField(
        queryset=ProductVariant.objects.select_related("product__category"), source="variant"
    )
    quantity = serializers.IntegerField(min_value=1, default=1)


class CartQuantitySerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)


class CartSerializer(serializers.Serializer):
    items = CartItemSerializer(many=True)
    subtotal = serializers.IntegerField()
    shipping_cost = serializers.IntegerField()
    total = serializers.IntegerField()


class AddressSerializer(serializers.ModelSerializer):
    # Declared explicitly so user input like "+98912..." or "۱۱۱۱۱-۲۲۲۲۲" is
    # normalized first; the model's length/format validators would reject it raw.
    recipient_phone = PhoneField(max_length=20)
    postal_code = serializers.CharField(max_length=20)

    class Meta:
        model = Address
        fields = ("id", "title", "recipient_name", "recipient_phone", "province", "city", "address", "postal_code", "is_default")

    def validate_postal_code(self, value):
        value = value.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
        value = value.replace("-", "").replace(" ", "").strip()
        if not (len(value) == 10 and value.isdigit()):
            raise serializers.ValidationError("کد پستی باید ۱۰ رقم باشد.")
        return value


class CheckoutSerializer(serializers.Serializer):
    address_id = serializers.IntegerField()
    note = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")


class OrderItemSerializer(serializers.ModelSerializer):
    line_total = serializers.IntegerField(read_only=True)

    class Meta:
        model = OrderItem
        fields = ("product_name", "variant_label", "unit_price", "quantity", "line_total")


class OrderSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            "number", "status", "status_label", "items", "subtotal", "shipping_cost", "total",
            "recipient_name", "recipient_phone", "province", "city", "address", "postal_code", "note",
            "reserved_until", "paid_at", "tracking_code", "created_at",
        )
