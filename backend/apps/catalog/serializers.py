from drf_spectacular.utils import extend_schema_field, inline_serializer
from rest_framework import serializers

from apps.core.fields import MediaURLField
from apps.tryon.providers import available_tryon_types

from .models import Banner, Category, Favorite, HomeShortcut, Product, ProductImage, ProductVariant


class CategorySerializer(serializers.ModelSerializer):
    icon = MediaURLField(read_only=True)
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ("id", "name", "slug", "icon", "tryon_type", "children")

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_children(self, obj) -> list:
        children = [c for c in obj.children.all() if c.is_active]
        return CategorySerializer(children, many=True, context=self.context).data


class CategoryBriefSerializer(serializers.ModelSerializer):
    icon = MediaURLField(read_only=True)

    class Meta:
        model = Category
        fields = ("id", "name", "slug", "icon")


class ProductVariantSerializer(serializers.ModelSerializer):
    price = serializers.IntegerField(read_only=True)
    in_stock = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = ("id", "size", "color", "color_hex", "price", "in_stock", "stock")

    def get_in_stock(self, obj) -> bool:
        return obj.stock > 0


class ProductImageSerializer(serializers.ModelSerializer):
    image = MediaURLField(read_only=True)

    class Meta:
        model = ProductImage
        fields = ("id", "image", "alt")


class _FavoriteFlagMixin(serializers.Serializer):
    is_favorite = serializers.SerializerMethodField()

    def get_is_favorite(self, obj) -> bool:
        favorite_ids = self.context.get("favorite_ids")
        return obj.pk in favorite_ids if favorite_ids is not None else False


class ProductListSerializer(_FavoriteFlagMixin, serializers.ModelSerializer):
    image = MediaURLField(read_only=True)
    category = CategoryBriefSerializer(read_only=True)
    supports_tryon = serializers.SerializerMethodField()
    discount_percent = serializers.IntegerField(read_only=True)
    in_stock = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id", "name", "slug", "image", "price", "compare_at_price", "discount_percent",
            "category", "supports_tryon", "in_stock", "is_favorite",
        )

    def get_supports_tryon(self, obj) -> bool:
        """True only if the product allows try-on AND the active AI engine can do its type."""
        return obj.supports_tryon and obj.effective_tryon_type in available_tryon_types()

    def get_in_stock(self, obj) -> bool:
        return any(v.is_active and v.stock > 0 for v in obj.variants.all())


class ProductDetailSerializer(ProductListSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    variants = serializers.SerializerMethodField()
    tryon_type = serializers.CharField(source="effective_tryon_type", read_only=True)

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + ("description", "images", "variants", "tryon_type")

    @extend_schema_field(ProductVariantSerializer(many=True))
    def get_variants(self, obj):
        active = [v for v in obj.variants.all() if v.is_active]
        return ProductVariantSerializer(active, many=True).data


class _LinkSerializerMixin(serializers.Serializer):
    link = serializers.SerializerMethodField()

    @extend_schema_field(inline_serializer("Link", {"type": serializers.ChoiceField(choices=["product", "category", "url", "none"]), "slug": serializers.CharField(required=False), "url": serializers.URLField(required=False)}))
    def get_link(self, obj):
        """Tell the app where a tap should navigate, in one normalized object."""
        if obj.link_type == obj.LinkType.PRODUCT and obj.product_id:
            return {"type": "product", "slug": obj.product.slug}
        if obj.link_type == obj.LinkType.CATEGORY and obj.category_id:
            return {"type": "category", "slug": obj.category.slug}
        if obj.link_type == obj.LinkType.URL and obj.url:
            return {"type": "url", "url": obj.url}
        return {"type": "none"}


class BannerSerializer(_LinkSerializerMixin, serializers.ModelSerializer):
    image = MediaURLField(read_only=True)

    class Meta:
        model = Banner
        fields = ("id", "title", "image", "position", "link")


class HomeShortcutSerializer(_LinkSerializerMixin, serializers.ModelSerializer):
    icon = MediaURLField(read_only=True)

    class Meta:
        model = HomeShortcut
        fields = ("id", "title", "icon", "link")


class FavoriteSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.visible(), source="product", write_only=True
    )

    class Meta:
        model = Favorite
        fields = ("id", "product", "product_id", "created_at")
        read_only_fields = ("id", "created_at")
