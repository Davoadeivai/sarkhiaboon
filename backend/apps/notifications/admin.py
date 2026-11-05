from django.contrib import admin

from .models import PushDevice


@admin.register(PushDevice)
class PushDeviceAdmin(admin.ModelAdmin):
    list_display = ("user", "platform", "is_active", "updated_at")
    list_filter = ("platform", "is_active")
    search_fields = ("user__phone",)
    readonly_fields = ("user", "token", "platform", "created_at", "updated_at")

    def has_add_permission(self, request):
        return False
