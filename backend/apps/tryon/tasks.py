"""
Background work, run by the Celery worker (never inside a web request).
"""
import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from .imaging import apply_watermark, read_file_bytes
from .models import PersonPhoto, TryOnJob
from .providers import ProviderError, TryOnRequest, get_provider

logger = logging.getLogger(__name__)

GENERIC_FAILURE = "پردازش تصویر با خطا مواجه شد. لطفاً دوباره تلاش کنید؛ این پرو از سهمیه‌ی شما کم نشد."
INPUT_FAILURE = "امکان پرو با این عکس وجود ندارد. لطفاً یک عکس تمام‌قد و روبه‌رو بگیرید."


def _fail(job, user_message, detail):
    job.status = TryOnJob.Status.FAILED
    job.error_message = user_message
    job.error_detail = detail[:5000]
    job.finished_at = timezone.now()
    job.save(update_fields=["status", "error_message", "error_detail", "finished_at"])
    _maybe_delete_photo(job)


def _maybe_delete_photo(job):
    """With retention 0, delete the customer photo once no job still needs it."""
    if settings.TRYON["PERSON_PHOTO_RETENTION_HOURS"] > 0 or not job.person_photo_id:
        return
    still_needed = TryOnJob.objects.filter(
        person_photo_id=job.person_photo_id,
        status__in=(TryOnJob.Status.QUEUED, TryOnJob.Status.PROCESSING),
    ).exists()
    if not still_needed:
        PersonPhoto.objects.filter(pk=job.person_photo_id).delete()


@shared_task(bind=True, acks_late=True)
def process_tryon_job(self, job_id):
    with transaction.atomic():
        # of=("self",): PostgreSQL cannot lock the nullable side of the joins
        job = TryOnJob.objects.select_for_update(of=("self",)).select_related("person_photo", "product__category").filter(pk=job_id).first()
        if job is None or job.is_finished:
            return  # deleted, or already handled by a duplicate delivery
        if job.person_photo is None:
            _fail(job, "عکس شما دیگر در دسترس نیست. لطفاً دوباره عکس بگیرید.", "person photo was deleted before processing")
            return
        job.status = TryOnJob.Status.PROCESSING
        job.started_at = job.started_at or timezone.now()
        job.attempts += 1
        job.save(update_fields=["status", "started_at", "attempts"])

    provider = get_provider()
    request = TryOnRequest(
        person_image=read_file_bytes(job.person_photo.image),
        garment_image=read_file_bytes(job.product.tryon_garment_image),
        category=job.tryon_type,
        job_id=str(job.pk),
    )

    try:
        result = provider.generate(request)
    except ProviderError as exc:
        max_retries = settings.TRYON["MAX_RETRIES"]
        if exc.retryable and self.request.retries < max_retries:
            logger.warning("Try-on %s failed (attempt %s), retrying: %s", job.pk, job.attempts, exc)
            TryOnJob.objects.filter(pk=job.pk).update(status=TryOnJob.Status.QUEUED)
            raise self.retry(exc=exc, countdown=5 * (2 ** self.request.retries), max_retries=max_retries)
        logger.error("Try-on %s failed permanently: %s", job.pk, exc)
        _fail(job, GENERIC_FAILURE if exc.retryable else INPUT_FAILURE, str(exc))
        return
    except Exception as exc:  # unexpected bug: never leave the customer waiting forever
        logger.exception("Unexpected error in try-on %s", job.pk)
        _fail(job, GENERIC_FAILURE, repr(exc))
        return

    image_bytes, extension = result.image, result.extension
    watermarked, wm_ext = apply_watermark(image_bytes)
    if wm_ext:
        image_bytes, extension = watermarked, wm_ext

    job.result_image.save(f"result.{extension}", ContentFile(image_bytes), save=False)
    job.status = TryOnJob.Status.COMPLETED
    job.finished_at = timezone.now()
    job.generation_seconds = round((job.finished_at - job.started_at).total_seconds(), 2)
    job.provider_meta = {**result.meta, "inference_seconds": result.inference_seconds}
    job.error_message = ""
    job.save()
    _maybe_delete_photo(job)


@shared_task
def purge_expired_person_images():
    """Delete customer photos past their retention period (privacy)."""
    expired = PersonPhoto.objects.filter(expires_at__lte=timezone.now())
    # Keep photos a running job is still reading
    busy = TryOnJob.objects.filter(status__in=(TryOnJob.Status.QUEUED, TryOnJob.Status.PROCESSING)).values("person_photo_id")
    count = 0
    for photo in expired.exclude(pk__in=busy):
        photo.delete()  # file removed by the post_delete signal
        count += 1
    if count:
        logger.info("Purged %s expired person photos", count)
    return count


@shared_task
def expire_stale_jobs():
    """Mark jobs stuck in the queue (e.g. worker crashed) as failed so the app stops waiting."""
    cutoff = timezone.now() - timedelta(minutes=settings.TRYON["STALE_JOB_MINUTES"])
    stale = TryOnJob.objects.filter(
        status__in=(TryOnJob.Status.QUEUED, TryOnJob.Status.PROCESSING), created_at__lt=cutoff
    )
    count = 0
    for job in stale:
        _fail(job, GENERIC_FAILURE, "job exceeded STALE_JOB_MINUTES")
        count += 1
    return count
