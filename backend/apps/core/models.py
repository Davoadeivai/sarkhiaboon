from django.db import models


class TimeStampedModel(models.Model):
    """Adds created/updated timestamps to every model that inherits it."""

    created_at = models.DateTimeField("تاریخ ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین تغییر", auto_now=True)

    class Meta:
        abstract = True
