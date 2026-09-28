"""Try-on business logic: photo upload, quota, result cache, job creation."""
import hashlib
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from .imaging import file_sha256, normalize_person_photo
from .models import PersonPhoto, TryOnJob
from .providers import get_provider


class TryOnNotAllowed(Exception):
    """Carries a Persian, user-facing reason. `code` lets the app react specifically."""

    def __init__(self, message, code="not_allowed", status=400):
        super().__init__(message)
        self.code = code
        self.status = status


# ---------------------------------------------------------------------------
# Photos
# ---------------------------------------------------------------------------
@transaction.atomic
def upload_person_photo(user, uploaded_file):
    """Validate, clean (EXIF/GPS removed) and store a customer photo."""
    photo = normalize_person_photo(uploaded_file)  # raises PhotoRejected
    record = PersonPhoto(user=user, content_hash=photo.content_hash, width=photo.width, height=photo.height)
    record.image.save("person.jpg", ContentFile(photo.data), save=False)
    record.save()
    return record


# ---------------------------------------------------------------------------
# Quota
# ---------------------------------------------------------------------------
@dataclass
class Quota:
    limit: int
    used: int

    @property
    def remaining(self):
        return max(0, self.limit - self.used)


def get_quota(user):
    """
    Daily try-on allowance. Results served from the cache and failed jobs do
    not count — the customer should not lose a try-on for our own error.
    """
    cfg = settings.TRYON
    limit = cfg["GUEST_DAILY_LIMIT"] if user.is_guest else cfg["USER_DAILY_LIMIT"]
    start_of_day = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    used = (
        TryOnJob.objects.filter(user=user, created_at__gte=start_of_day, from_cache=False)
        .exclude(status=TryOnJob.Status.FAILED)
        .count()
    )
    return Quota(limit=limit, used=used)


# ---------------------------------------------------------------------------
# Result cache
# ---------------------------------------------------------------------------
def _garment_hash(product):
    image = product.tryon_garment_image
    return cache.get_or_set(f"tryon:garment-hash:{image.name}", lambda: file_sha256(image), 60 * 60 * 24)


def build_cache_key(photo, product, provider):
    raw = f"{photo.content_hash}:{_garment_hash(product)}:{product.effective_tryon_type}:{provider.name}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _find_cached_result(cache_key):
    return (
        TryOnJob.objects.filter(cache_key=cache_key, status=TryOnJob.Status.COMPLETED)
        .exclude(result_image="")
        .order_by("-finished_at")
        .first()
    )


# ---------------------------------------------------------------------------
# Job creation
# ---------------------------------------------------------------------------
@transaction.atomic
def create_job(user, product, photo):
    if photo.user_id != user.pk:
        raise TryOnNotAllowed("این عکس متعلق به شما نیست.", code="photo_not_found", status=404)
    if photo.expires_at <= timezone.now():
        raise TryOnNotAllowed("عکس شما منقضی شده است. لطفاً دوباره عکس بگیرید.", code="photo_expired")
    if not product.is_active or not product.supports_tryon:
        raise TryOnNotAllowed("پرو مجازی برای این محصول فعال نیست.", code="product_not_supported")

    provider = get_provider()
    tryon_type = product.effective_tryon_type
    if not provider.supports(tryon_type):
        raise TryOnNotAllowed("پرو مجازی برای این نوع محصول هنوز فعال نشده است.", code="category_not_supported")

    job = TryOnJob(user=user, product=product, person_photo=photo, tryon_type=tryon_type, provider=provider.name)

    if settings.TRYON["ENABLE_RESULT_CACHE"]:
        job.cache_key = build_cache_key(photo, product, provider)
        cached = _find_cached_result(job.cache_key)
        if cached:
            now = timezone.now()
            job.status = TryOnJob.Status.COMPLETED
            job.from_cache = True
            job.result_image.name = cached.result_image.name  # shared file, no GPU call
            job.generation_seconds = 0
            job.started_at = job.finished_at = now
            job.save()
            return job

    # Lock the user's row so two simultaneous requests cannot both pass the quota check
    type(user).objects.select_for_update().filter(pk=user.pk).first()
    quota = get_quota(user)
    if quota.remaining <= 0:
        message = (
            "سهمیه‌ی پرو رایگان امروز شما تمام شده است. برای ادامه، با شماره موبایل وارد شوید."
            if user.is_guest
            else "سهمیه‌ی پرو امروز شما تمام شده است. فردا دوباره امتحان کنید."
        )
        raise TryOnNotAllowed(message, code="quota_exceeded", status=429)

    job.save()
    from .tasks import process_tryon_job  # local import avoids a circular import

    transaction.on_commit(lambda: process_tryon_job.delay(str(job.pk)))
    return job
