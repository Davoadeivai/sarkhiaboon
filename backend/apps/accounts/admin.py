from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import OTPCode, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("-date_joined",)
    list_display = ("__str__", "full_name", "is_guest", "is_active", "is_staff", "date_joined")
    list_filter = ("is_guest", "is_active", "is_staff")
    search_fields = ("phone", "first_name", "last_name")
    readonly_fields = ("date_joined", "last_login")
    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        ("اطلاعات شخصی", {"fields": ("first_name", "last_name", "is_guest")}),
        ("دسترسی‌ها", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("تاریخ‌ها", {"fields": ("date_joined", "last_login")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("phone", "password1", "password2", "is_staff")}),)


@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    list_display = ("phone", "created_at", "expires_at", "attempts", "is_used")
    list_filter = ("is_used",)
    search_fields = ("phone",)
    readonly_fields = ("phone", "code_hash", "created_at", "expires_at", "attempts", "is_used")

    def has_add_permission(self, request):
        return False
