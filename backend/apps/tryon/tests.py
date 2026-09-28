import base64
import os
import tempfile
from datetime import timedelta
from io import BytesIO
from unittest import mock

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from PIL import Image

from apps.accounts.models import User
from apps.accounts.signals import guest_merged
from apps.catalog.models import TryOnType
from apps.catalog.testing import make_category, make_product
from apps.core.testing import APITestBase, EagerCeleryMixin, make_image, tryon_settings

from . import tasks
from .imaging import PhotoRejected, normalize_person_photo, sharpness_score
from .models import PersonPhoto, TryOnJob
from .providers.base import ProviderError, TryOnRequest, TryOnResult
from .providers.mock import MockProvider
from .providers.runpod import RunPodProvider


class TryOnTestBase(EagerCeleryMixin, APITestBase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(phone="09121234567")
        self.product = make_product()
        self.authenticate(self.user)

    def upload_photo(self, image=None):
        resp = self.client.post("/api/v1/tryon/photos/", {"image": image or make_image()}, format="multipart")
        self.assertEqual(resp.status_code, 201, resp.data)
        return resp.data["id"]

    def start_job(self, photo_id, product=None):
        """POST a job, let the queued task run, then poll it like the app does."""
        with self.captureOnCommitCallbacks(execute=True):
            created = self.client.post(
                "/api/v1/tryon/jobs/", {"product_id": (product or self.product).pk, "photo_id": photo_id}, format="json"
            )
        if created.status_code not in (200, 202):
            return created
        self.last_create_status = created.status_code
        return self.client.get(f"/api/v1/tryon/jobs/{created.data['id']}/")


# ---------------------------------------------------------------------------
# Photo checks
# ---------------------------------------------------------------------------
class PhotoValidationTests(TestCase):
    def _reject(self, upload, fragment):
        with self.assertRaises(PhotoRejected) as ctx:
            normalize_person_photo(upload)
        self.assertIn(fragment, str(ctx.exception))

    def test_valid_photo_is_normalized_to_jpeg(self):
        result = normalize_person_photo(make_image("p.png", (800, 1200), fmt="PNG"))
        image = Image.open(BytesIO(result.data))
        self.assertEqual(image.format, "JPEG")
        self.assertEqual(len(result.content_hash), 64)

    def test_exif_including_gps_is_removed_and_rotation_applied(self):
        exif = Image.Exif()
        exif[0x0112] = 6  # orientation: rotate 90° (camera held sideways)
        exif[0x010E] = "secret description"
        buffer = BytesIO()
        Image.new("RGB", (1200, 800), (150, 120, 100)).save(buffer, format="JPEG", exif=exif)
        # stored landscape but EXIF says rotate -> becomes portrait, so it passes the portrait check
        with tryon_settings(MIN_SHARPNESS=0):
            result = normalize_person_photo(SimpleUploadedFile("r.jpg", buffer.getvalue(), "image/jpeg"))
        image = Image.open(BytesIO(result.data))
        self.assertEqual((image.width, image.height), (800, 1200))
        self.assertEqual(len(image.getexif()), 0)

    def test_large_photo_is_downscaled(self):
        with tryon_settings(MAX_SIDE=1000):
            result = normalize_person_photo(make_image(size=(1500, 2000)))
        self.assertEqual(max(result.width, result.height), 1000)

    def test_rejections(self):
        self._reject(make_image(size=(200, 300)), "کیفیت عکس پایین")
        self._reject(make_image(size=(1200, 700)), "عمودی")
        self._reject(make_image(color=(10, 10, 10)), "تاریک")
        self._reject(make_image(color=(250, 250, 250), textured=False), "روشن")
        self._reject(make_image(color=(120, 120, 120), textured=False), "تار")
        self._reject(SimpleUploadedFile("x.jpg", b"not an image", "image/jpeg"), "معتبر نیست")
        gif = BytesIO()
        Image.new("RGB", (800, 1200)).save(gif, format="GIF")
        self._reject(SimpleUploadedFile("x.gif", gif.getvalue(), "image/gif"), "فرمت")
        with tryon_settings(MAX_UPLOAD_MB=0):
            self._reject(make_image(), "حجم")

    def test_sharpness_score_separates_flat_and_textured(self):
        flat = Image.new("RGB", (400, 600), (120, 120, 120))
        textured = Image.open(make_image(size=(400, 600)))
        self.assertLess(sharpness_score(flat), 1)
        self.assertGreater(sharpness_score(textured), 100)


# ---------------------------------------------------------------------------
# End-to-end flow with the mock engine
# ---------------------------------------------------------------------------
class TryOnFlowTests(TryOnTestBase):
    def test_upload_list_and_delete_photo(self):
        photo_id = self.upload_photo()
        listing = self.client.get("/api/v1/tryon/photos/")
        self.assertEqual([p["id"] for p in listing.data], [photo_id])
        path = PersonPhoto.objects.get(pk=photo_id).image.path
        self.assertTrue(os.path.exists(path))
        self.assertEqual(self.client.delete(f"/api/v1/tryon/photos/{photo_id}/").status_code, 204)
        self.assertFalse(os.path.exists(path))

    def test_rejected_photo_returns_reason(self):
        resp = self.client.post("/api/v1/tryon/photos/", {"image": make_image(size=(200, 300))}, format="multipart")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["code"], "photo_rejected")

    def test_full_tryon_completes(self):
        resp = self.start_job(self.upload_photo())
        self.assertEqual(self.last_create_status, 202)  # accepted, processed in the background
        self.assertEqual(resp.data["status"], "completed")
        self.assertEqual(resp.data["status_label"], "آماده شد")
        self.assertTrue(resp.data["result_image"].startswith("http://"))
        self.assertFalse(resp.data["from_cache"])
        job = TryOnJob.objects.get(pk=resp.data["id"])
        self.assertEqual(job.provider, "mock")
        self.assertEqual(job.tryon_type, "upper_body")
        self.assertIsNotNone(job.generation_seconds)
        Image.open(job.result_image.path).verify()

        poll = self.client.get(f"/api/v1/tryon/jobs/{job.pk}/")
        self.assertEqual(poll.data["status"], "completed")

    def test_queued_job_reports_queue_position(self):
        photo = PersonPhoto.objects.get(pk=self.upload_photo())
        # Without running on-commit callbacks, the job stays queued
        first = self.client.post("/api/v1/tryon/jobs/", {"product_id": self.product.pk, "photo_id": str(photo.pk)}, format="json")
        self.assertEqual(first.status_code, 202)
        self.assertEqual(first.data["status"], "queued")
        self.assertEqual(first.data["queue_position"], 1)

    def test_identical_request_is_served_from_cache(self):
        photo_id = self.upload_photo()
        first = self.start_job(photo_id)
        with mock.patch.object(MockProvider, "generate") as engine:
            second = self.start_job(photo_id)
            engine.assert_not_called()  # no GPU call
        self.assertEqual(self.last_create_status, 200)  # answered instantly
        self.assertTrue(second.data["from_cache"])
        self.assertEqual(second.data["result_image"], first.data["result_image"])
        self.assertEqual(self.client.get("/api/v1/tryon/quota/").data["used"], 1)

    def test_deleting_a_cached_job_keeps_the_shared_file(self):
        photo_id = self.upload_photo()
        original = TryOnJob.objects.get(pk=self.start_job(photo_id).data["id"])
        cached = TryOnJob.objects.get(pk=self.start_job(photo_id).data["id"])
        path = original.result_image.path
        self.client.delete(f"/api/v1/tryon/jobs/{cached.pk}/")
        self.assertTrue(os.path.exists(path))
        self.client.delete(f"/api/v1/tryon/jobs/{original.pk}/")
        self.assertFalse(os.path.exists(path))

    def test_product_without_tryon_is_rejected(self):
        bag = make_product("کیف", category=make_category("کیف", TryOnType.NONE))
        resp = self.start_job(self.upload_photo(), product=bag)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["code"], "product_not_supported")

    def test_unsupported_category_is_rejected(self):
        shoes = make_product("کتانی", category=make_category("کفش", TryOnType.SHOES))
        resp = self.start_job(self.upload_photo(), product=shoes)
        self.assertEqual(resp.data["code"], "category_not_supported")

    def test_cannot_use_someone_elses_photo(self):
        other = User.objects.create_user(phone="09350000000")
        self.authenticate(other)
        photo_id = self.upload_photo()
        self.authenticate(self.user)
        self.assertEqual(self.start_job(photo_id).status_code, 404)
        self.assertEqual(self.client.get(f"/api/v1/tryon/photos/").data, [])

    def test_expired_photo_is_rejected(self):
        photo_id = self.upload_photo()
        PersonPhoto.objects.filter(pk=photo_id).update(expires_at=timezone.now() - timedelta(minutes=1))
        resp = self.start_job(photo_id)
        self.assertEqual(resp.data["code"], "photo_expired")

    def test_wardrobe_save_and_filter(self):
        job_id = self.start_job(self.upload_photo()).data["id"]
        self.assertTrue(self.client.post(f"/api/v1/tryon/jobs/{job_id}/save/").data["is_saved"])
        self.assertEqual(self.client.get("/api/v1/tryon/jobs/", {"saved": "true"}).data["count"], 1)
        self.assertFalse(self.client.delete(f"/api/v1/tryon/jobs/{job_id}/save/").data["is_saved"])
        self.assertEqual(self.client.get("/api/v1/tryon/jobs/", {"saved": "true"}).data["count"], 0)

    def test_jobs_are_private(self):
        job_id = self.start_job(self.upload_photo()).data["id"]
        self.authenticate(User.objects.create_user(phone="09350000000"))
        self.assertEqual(self.client.get(f"/api/v1/tryon/jobs/{job_id}/").status_code, 404)

    def test_guest_merge_moves_photos_and_jobs(self):
        guest = User.objects.create_guest()
        self.authenticate(guest)
        job_id = self.start_job(self.upload_photo()).data["id"]
        guest_merged.send(sender=User, guest=guest, user=self.user)
        self.assertEqual(TryOnJob.objects.get(pk=job_id).user, self.user)
        self.assertEqual(PersonPhoto.objects.filter(user=self.user).count(), 1)


# ---------------------------------------------------------------------------
# Quota
# ---------------------------------------------------------------------------
@tryon_settings(ENABLE_RESULT_CACHE=False, GUEST_DAILY_LIMIT=2, USER_DAILY_LIMIT=3)
class QuotaTests(TryOnTestBase):
    def test_guest_limit(self):
        self.authenticate(User.objects.create_guest())
        photo_id = self.upload_photo()
        self.assertEqual(self.start_job(photo_id).data["status"], "completed")
        self.assertEqual(self.start_job(photo_id).data["status"], "completed")
        blocked = self.start_job(photo_id)
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(blocked.data["code"], "quota_exceeded")
        self.assertIn("شماره موبایل", blocked.data["detail"])  # nudges the guest to register

    def test_user_limit_and_quota_endpoint(self):
        photo_id = self.upload_photo()
        for _ in range(3):
            self.start_job(photo_id)
        self.assertEqual(self.client.get("/api/v1/tryon/quota/").data, {"limit": 3, "used": 3, "remaining": 0})
        self.assertEqual(self.start_job(photo_id).status_code, 429)

    def test_failed_jobs_do_not_use_quota(self):
        photo_id = self.upload_photo()
        with mock.patch.object(MockProvider, "generate", side_effect=ProviderError("bad input", retryable=False)):
            for _ in range(4):
                self.assertEqual(self.start_job(photo_id).data["status"], "failed")
        self.assertEqual(self.client.get("/api/v1/tryon/quota/").data["used"], 0)


# ---------------------------------------------------------------------------
# Failures, retries, privacy and maintenance tasks
# ---------------------------------------------------------------------------
@tryon_settings(ENABLE_RESULT_CACHE=False)
class ReliabilityTests(TryOnTestBase):
    def test_temporary_failure_is_retried_then_succeeds(self):
        real = MockProvider().generate
        calls = []

        def flaky(request):
            calls.append(1)
            if len(calls) == 1:
                raise ProviderError("GPU busy", retryable=True)
            return real(request)

        with mock.patch.object(MockProvider, "generate", side_effect=flaky):
            resp = self.start_job(self.upload_photo())
        self.assertEqual(resp.data["status"], "completed")
        self.assertEqual(len(calls), 2)
        self.assertEqual(TryOnJob.objects.get(pk=resp.data["id"]).attempts, 2)

    def test_retries_exhausted_gives_friendly_error(self):
        with tryon_settings(ENABLE_RESULT_CACHE=False, MAX_RETRIES=2):
            with mock.patch.object(MockProvider, "generate", side_effect=ProviderError("down", retryable=True)) as engine:
                resp = self.start_job(self.upload_photo())
        self.assertEqual(engine.call_count, 3)  # first try + 2 retries
        job = TryOnJob.objects.get(pk=resp.data["id"])
        self.assertEqual(job.status, "failed")
        self.assertIn("از سهمیه‌ی شما کم نشد", job.error_message)
        self.assertIn("down", job.error_detail)  # technical detail kept for staff only
        self.assertNotIn("error_detail", resp.data)

    def test_bad_input_is_not_retried(self):
        with mock.patch.object(MockProvider, "generate", side_effect=ProviderError("no person", retryable=False)) as engine:
            resp = self.start_job(self.upload_photo())
        self.assertEqual(engine.call_count, 1)
        self.assertIn("عکس تمام‌قد", resp.data["error_message"])

    def test_unexpected_bug_marks_job_failed(self):
        with mock.patch.object(MockProvider, "generate", side_effect=ZeroDivisionError()):
            resp = self.start_job(self.upload_photo())
        self.assertEqual(resp.data["status"], "failed")

    def test_zero_retention_deletes_photo_after_processing(self):
        with tryon_settings(ENABLE_RESULT_CACHE=False, PERSON_PHOTO_RETENTION_HOURS=0):
            photo_id = self.upload_photo()
            path = PersonPhoto.objects.get(pk=photo_id).image.path
            resp = self.start_job(photo_id)
        self.assertEqual(resp.data["status"], "completed")
        self.assertFalse(PersonPhoto.objects.filter(pk=photo_id).exists())
        self.assertFalse(os.path.exists(path))

    def test_purge_expired_photos_keeps_busy_ones(self):
        expired_id = self.upload_photo()
        busy_id = self.upload_photo(make_image(color=(170, 130, 110)))
        PersonPhoto.objects.update(expires_at=timezone.now() - timedelta(hours=1))
        busy = PersonPhoto.objects.get(pk=busy_id)
        TryOnJob.objects.create(user=self.user, product=self.product, person_photo=busy, tryon_type="upper_body")
        self.assertEqual(tasks.purge_expired_person_images(), 1)
        self.assertFalse(PersonPhoto.objects.filter(pk=expired_id).exists())
        self.assertTrue(PersonPhoto.objects.filter(pk=busy_id).exists())

    def test_stale_jobs_are_failed(self):
        photo = PersonPhoto.objects.get(pk=self.upload_photo())
        job = TryOnJob.objects.create(user=self.user, product=self.product, person_photo=photo, tryon_type="upper_body")
        TryOnJob.objects.filter(pk=job.pk).update(created_at=timezone.now() - timedelta(hours=1))
        self.assertEqual(tasks.expire_stale_jobs(), 1)
        job.refresh_from_db()
        self.assertEqual(job.status, "failed")

    def test_duplicate_task_delivery_is_ignored(self):
        job_id = self.start_job(self.upload_photo()).data["id"]
        with mock.patch.object(MockProvider, "generate") as engine:
            tasks.process_tryon_job.delay(job_id)
            engine.assert_not_called()

    def test_watermark_is_applied_when_configured(self):
        logo = Image.new("RGBA", (200, 80), (255, 0, 0, 255))
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as fh:
            logo.save(fh, format="PNG")
        try:
            with tryon_settings(ENABLE_RESULT_CACHE=False, WATERMARK_IMAGE=fh.name):
                job = TryOnJob.objects.get(pk=self.start_job(self.upload_photo()).data["id"])
            result = Image.open(job.result_image.path).convert("RGB")
            r, g, b = result.getpixel((result.width // 40 + 5, result.height - result.width // 40 - 5))
            self.assertGreater(r, g + 40)  # reddish logo blended into the bottom-left corner
        finally:
            os.unlink(fh.name)


# ---------------------------------------------------------------------------
# RunPod client (no network: a fake session replays RunPod's responses)
# ---------------------------------------------------------------------------
class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code, self._payload, self.text = status_code, payload, str(payload)

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.responses.pop(0)


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


RUNPOD = dict(RUNPOD_ENDPOINT_ID="abc123", RUNPOD_API_KEY="key", RUNPOD_POLL_INTERVAL_SECONDS=2, PROVIDER_TIMEOUT_SECONDS=10)


@tryon_settings(**RUNPOD)
class RunPodProviderTests(TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.request = TryOnRequest(person_image=b"person", garment_image=b"garment", category="upper_body", job_id="j1")
        self.png = base64.b64encode(b"\x89PNG-result").decode()

    def provider(self, responses):
        self.session = FakeSession(responses)
        return RunPodProvider(session=self.session, sleep=self.clock.sleep, clock=self.clock.time)

    def test_success_after_polling(self):
        provider = self.provider([
            FakeResponse(200, {"id": "rp1", "status": "IN_QUEUE"}),
            FakeResponse(200, {"id": "rp1", "status": "IN_PROGRESS"}),
            FakeResponse(200, {"id": "rp1", "status": "COMPLETED", "delayTime": 31000, "executionTime": 7800,
                               "output": {"image": self.png, "format": "png"}}),
        ])
        result = provider.generate(self.request)
        self.assertEqual(result.image, b"\x89PNG-result")
        self.assertEqual(result.extension, "png")
        self.assertEqual(result.inference_seconds, 7.8)
        self.assertEqual(result.meta["delay_ms"], 31000)  # cold start + queue is measured

        method, url, kwargs = self.session.calls[0]
        self.assertEqual((method, url), ("POST", "https://api.runpod.ai/v2/abc123/run"))
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer key")
        sent = kwargs["json"]["input"]
        self.assertEqual(base64.b64decode(sent["person_image"]), b"person")
        self.assertEqual(sent["category"], "upper_body")
        self.assertEqual(self.session.calls[1][1], "https://api.runpod.ai/v2/abc123/status/rp1")

    def test_timeout_cancels_and_is_retryable(self):
        provider = self.provider([FakeResponse(200, {"id": "rp1", "status": "IN_QUEUE"})]
                                 + [FakeResponse(200, {"id": "rp1", "status": "IN_QUEUE"})] * 5
                                 + [FakeResponse(200, {})])
        with self.assertRaises(ProviderError) as ctx:
            provider.generate(self.request)
        self.assertTrue(ctx.exception.retryable)
        self.assertEqual(self.session.calls[-1][1], "https://api.runpod.ai/v2/abc123/cancel/rp1")

    def test_bad_api_key_is_not_retryable(self):
        with self.assertRaises(ProviderError) as ctx:
            self.provider([FakeResponse(401, {"error": "unauthorized"})]).generate(self.request)
        self.assertFalse(ctx.exception.retryable)

    def test_server_error_is_retryable(self):
        with self.assertRaises(ProviderError) as ctx:
            self.provider([FakeResponse(503, None)]).generate(self.request)
        self.assertTrue(ctx.exception.retryable)

    def test_worker_reported_error_is_not_retryable(self):
        provider = self.provider([
            FakeResponse(200, {"id": "rp1", "status": "COMPLETED", "output": {"error": "no person detected"}}),
        ])
        with self.assertRaises(ProviderError) as ctx:
            provider.generate(self.request)
        self.assertFalse(ctx.exception.retryable)

    def test_failed_job_is_retryable(self):
        provider = self.provider([FakeResponse(200, {"id": "rp1", "status": "FAILED", "error": "OOM"})])
        with self.assertRaises(ProviderError) as ctx:
            provider.generate(self.request)
        self.assertTrue(ctx.exception.retryable)

    def test_missing_configuration(self):
        with tryon_settings(RUNPOD_ENDPOINT_ID="", RUNPOD_API_KEY=""):
            with self.assertRaises(ProviderError) as ctx:
                RunPodProvider(session=FakeSession([])).generate(self.request)
        self.assertFalse(ctx.exception.retryable)

    def test_shoes_are_refused_before_any_network_call(self):
        provider = self.provider([])
        with self.assertRaises(ProviderError):
            provider.generate(TryOnRequest(b"p", b"g", "shoes", "j2"))
        self.assertEqual(self.session.calls, [])


class AdminSmokeTests(TryOnTestBase):
    def test_admin_pages_render(self):
        self.start_job(self.upload_photo())
        admin = User.objects.create_superuser(phone="09120000000", password="pass-1234")
        self.client.credentials()
        self.client.force_login(admin)
        for url in ("/admin/tryon/tryonjob/", "/admin/tryon/personphoto/", "/admin/catalog/product/",
                    "/admin/catalog/banner/", "/admin/catalog/homeshortcut/", "/admin/accounts/user/"):
            self.assertEqual(self.client.get(url).status_code, 200, url)
        job = TryOnJob.objects.first()
        self.assertEqual(self.client.get(f"/admin/tryon/tryonjob/{job.pk}/change/").status_code, 200)
