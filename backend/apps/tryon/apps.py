from django.apps import AppConfig


class TryonConfig(AppConfig):
    name = "apps.tryon"
    label = "tryon"
    verbose_name = "پرو مجازی"

    def ready(self):
        from . import signals  # noqa: F401
