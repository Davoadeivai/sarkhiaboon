import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.catalog.models import Product, TryOnType


def person_photo_path(instance, filename):
    # Random names: the URL of a customer's photo must not be guessable.
    return f"tryon/people/{uuid.uuid4().hex}.jpg"


def result_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    return f"tryon/results/{uuid.uuid4().hex}.{ext}"


class PersonPhotoQuerySet(models.QuerySet):
    def live(self):
        return self.filter(expires_at__gt=timezone.now())


class PersonPhoto(models.Model):
    """
    A customer's own photo, uploaded once and reused for several try-ons.
    Deleted automatically after TRYON['PERSON_PHOTO_RETENTION_HOURS'].
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="person_photos")
    image = models.ImageField(upload_to=person_photo_path)
    content_hash = models.CharField(max_length=64, db_index=True)
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)

    objects = PersonPhotoQuerySet.as_manager()

    class Meta:
        verbose_name = "عکس کاربر"
        verbose_name_plural = "عکس‌های کاربران"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.user} — {self.created_at:%Y-%m-%d %H:%M}"

    def save(self, *args, **kwargs):
        if not self.expires_at:
            hours = settings.TRYON["PERSON_PHOTO_RETENTION_HOURS"]
            # With 0 hours the photo still needs a short grace window to be
            # used by the job that was just created; the job deletes it on finish.
            self.expires_at = timezone.now() + (timedelta(hours=hours) if hours > 0 else timedelta(minutes=30))
        super().save(*args, **kwargs)


class TryOnJob(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "در صف پردازش"
        PROCESSING = "processing", "در حال پرو لباس"
        COMPLETED = "completed", "آماده شد"
        FAILED = "failed", "ناموفق"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tryon_jobs")
    person_photo = models.ForeignKey(
        PersonPhoto, null=True, blank=True, on_delete=models.SET_NULL, related_name="jobs"
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="tryon_jobs")
    tryon_type = models.CharField(max_length=20, choices=TryOnType.choices)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.QUEUED, db_index=True)
    provider = models.CharField("موتور پردازش", max_length=60, blank=True)
    cache_key = models.CharField(max_length=64, db_index=True, blank=True)
    from_cache = models.BooleanField("از حافظه‌ی نتایج", default=False)
    result_image = models.ImageField(upload_to=result_path, blank=True)
    error_message = models.CharField("پیام خطا برای کاربر", max_length=255, blank=True)
    error_detail = models.TextField("جزئیات فنی خطا", blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    generation_seconds = models.FloatField("زمان پردازش (ثانیه)", null=True, blank=True)
    provider_meta = models.JSONField("اطلاعات فنی موتور", default=dict, blank=True)
    is_saved = models.BooleanField("ذخیره در کمد مجازی", default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "درخواست پرو"
        verbose_name_plural = "درخواست‌های پرو"
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("user", "created_at"))]

    def __str__(self):
        return f"{self.product} — {self.get_status_display()}"

    @property
    def is_finished(self):
        return self.status in (self.Status.COMPLETED, self.Status.FAILED)

    def queue_position(self):
        """1-based position among queued jobs, for 'you are number N in line'."""
        if self.status != self.Status.QUEUED:
            return None
        ahead = TryOnJob.objects.filter(status=self.Status.QUEUED, created_at__lt=self.created_at).count()
        return ahead + 1
