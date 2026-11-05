from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    name = "apps.notifications"
    label = "notifications"
    verbose_name = "اعلان‌ها"

    def ready(self):
        from . import signals  # noqa: F401
