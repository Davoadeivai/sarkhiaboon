from django.contrib import admin
from django.db.models import Avg, Count, Q
from django.utils.html import format_html

from .models import PersonPhoto, TryOnJob


@admin.register(TryOnJob)
class TryOnJobAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "product", "tryon_type", "status", "provider", "generation_seconds", "from_cache", "result_preview")
    list_filter = ("status", "provider", "tryon_type", "from_cache", "is_saved")
    search_fields = ("user__phone", "product__name", "id")
    date_hierarchy = "created_at"
    readonly_fields = [f.name for f in TryOnJob._meta.fields] + ["result_preview"]
    exclude = ("result_image",)

    def has_add_permission(self, request):
        return False

    @admin.display(description="نتیجه")
    def result_preview(self, obj):
        if not obj.result_image:
            return "—"
        return format_html('<a href="{0}" target="_blank"><img src="{0}" style="height:64px;border-radius:4px"/></a>', obj.result_image.url)

    def changelist_view(self, request, extra_context=None):
        """Summary line above the list: volume, failure rate, average time — the numbers that drive GPU cost."""
        stats = TryOnJob.objects.aggregate(
            total=Count("id"),
            failed=Count("id", filter=Q(status=TryOnJob.Status.FAILED)),
            cached=Count("id", filter=Q(from_cache=True)),
            avg_seconds=Avg("generation_seconds", filter=Q(status=TryOnJob.Status.COMPLETED, from_cache=False)),
        )
        extra_context = {**(extra_context or {}), "subtitle": (
            f"کل: {stats['total']} | ناموفق: {stats['failed']} | از حافظه (بدون هزینه‌ی GPU): {stats['cached']} | "
            f"میانگین زمان: {round(stats['avg_seconds'] or 0, 1)} ثانیه"
        )}
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(PersonPhoto)
class PersonPhotoAdmin(admin.ModelAdmin):
    """
    Deliberately shows no image preview: staff do not need to see customers'
    personal photos. Only metadata is visible, and photos can be deleted.
    """

    list_display = ("id", "user", "width", "height", "created_at", "expires_at")
    search_fields = ("user__phone",)
    readonly_fields = ("id", "user", "width", "height", "content_hash", "created_at", "expires_at")
    exclude = ("image",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
