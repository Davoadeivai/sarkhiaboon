from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class PushDevice(TimeStampedModel):
    """A phone that can receive push notifications for a user (guest or registered)."""

    class Platform(models.TextChoices):
        ANDROID = "android", "اندروید"
        IOS = "ios", "آیفون"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="push_devices")
    # A token identifies one app install; it moves to whoever is logged in on that phone.
    token = models.CharField("توکن", max_length=255, unique=True)
    platform = models.CharField("سیستم‌عامل", max_length=10, choices=Platform.choices)
    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        verbose_name = "دستگاه اعلان"
        verbose_name_plural = "دستگاه‌های اعلان"

    def __str__(self):
        return f"{self.user} — {self.get_platform_display()}"
