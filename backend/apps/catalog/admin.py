from django.contrib import admin
from django.db.models import Sum
from django.utils.html import format_html

from .models import Banner, Category, Favorite, HomeShortcut, Product, ProductImage, ProductVariant


def _thumb(image, size=48):
    if not image:
        return "—"
    return format_html('<img src="{}" style="height:{}px;border-radius:4px" />', image.url, size)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("__str__", "icon_preview", "tryon_type", "show_on_home", "order", "is_active")
    list_editable = ("show_on_home", "order", "is_active")
    list_filter = ("is_active", "show_on_home", "tryon_type")
    search_fields = ("name",)
    autocomplete_fields = ("parent",)

    @admin.display(description="آیکون")
    def icon_preview(self, obj):
        return _thumb(obj.icon, 32)


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ("size", "color", "color_hex", "sku", "stock", "price_override", "is_active")


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ("image", "alt", "order")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("image_preview", "name", "category", "price", "compare_at_price", "total_stock", "tryon_enabled", "is_active")
    list_display_links = ("image_preview", "name")
    list_editable = ("price", "is_active")
    list_filter = ("is_active", "tryon_enabled", "category")
    search_fields = ("name", "description", "variants__sku")
    autocomplete_fields = ("category",)
    inlines = (ProductVariantInline, ProductImageInline)
    fieldsets = (
        (None, {"fields": ("name", "slug", "category", "description")}),
        ("قیمت", {"fields": ("price", "compare_at_price")}),
        ("تصاویر", {"fields": ("image", "garment_image")}),
        ("پرو مجازی", {"fields": ("tryon_enabled", "tryon_type")}),
        ("وضعیت", {"fields": ("is_active",)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("category").annotate(_stock=Sum("variants__stock"))

    @admin.display(description="تصویر")
    def image_preview(self, obj):
        return _thumb(obj.image)

    @admin.display(description="موجودی کل", ordering="_stock")
    def total_stock(self, obj):
        return obj._stock or 0


class _ScheduledAdmin(admin.ModelAdmin):
    list_filter = ("is_active", "link_type")
    fieldsets = (
        (None, {"fields": ("title",)}),
        ("لینک", {"fields": ("link_type", "product", "category", "url"), "description": "با زدن روی این مورد، کاربر به کجا برود."}),
        ("زمان‌بندی نمایش", {"fields": ("is_active", "starts_at", "ends_at", "order")}),
    )
    autocomplete_fields = ("product", "category")


@admin.register(Banner)
class BannerAdmin(_ScheduledAdmin):
    list_display = ("image_preview", "title", "position", "order", "is_active", "starts_at", "ends_at")
    list_editable = ("order", "is_active")
    list_filter = ("is_active", "position", "link_type")
    fieldsets = ((None, {"fields": ("title", "image", "position")}),) + _ScheduledAdmin.fieldsets[1:]

    @admin.display(description="تصویر")
    def image_preview(self, obj):
        return _thumb(obj.image, 40)


@admin.register(HomeShortcut)
class HomeShortcutAdmin(_ScheduledAdmin):
    list_display = ("icon_preview", "title", "order", "is_active", "starts_at", "ends_at")
    list_editable = ("order", "is_active")
    fieldsets = ((None, {"fields": ("title", "icon")}),) + _ScheduledAdmin.fieldsets[1:]

    @admin.display(description="آیکون")
    def icon_preview(self, obj):
        return _thumb(obj.icon, 32)


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "created_at")
    search_fields = ("user__phone", "product__name")
    autocomplete_fields = ("user", "product")
