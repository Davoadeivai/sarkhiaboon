"""Shared helpers for the test suites of all apps."""
import shutil
import tempfile
from io import BytesIO
from unittest import mock

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image, ImageDraw
from rest_framework.test import APIClient
from rest_framework.throttling import SimpleRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken

_RELAXED_RATES = {"otp_request": "1000/hour", "otp_verify": "1000/hour", "guest_login": "1000/hour"}


class APITestBase(TestCase):
    """
    - Clears the throttle cache and relaxes rate limits (DRF reads rates at
      import time, so override_settings alone does not change them).
    - Stores uploaded media in a temporary folder that is deleted afterwards.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._media_dir = tempfile.mkdtemp(prefix="sarkhiaboon-test-media-")
        cls._media_override = override_settings(MEDIA_ROOT=cls._media_dir)
        cls._media_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls._media_override.disable()
        shutil.rmtree(cls._media_dir, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        cache.clear()
        patcher = mock.patch.dict(SimpleRateThrottle.THROTTLE_RATES, _RELAXED_RATES)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = APIClient()

    def authenticate(self, user):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")


def make_image(name="photo.jpg", size=(768, 1024), color=(180, 140, 120), fmt="JPEG", textured=True):
    """
    Return an in-memory uploaded image file of the given size.

    Textured images pass the try-on sharpness check; use textured=False for a
    flat single-colour image (e.g. to test blur/darkness rejection).
    """
    image = Image.new("RGB", size, color)
    if textured:
        draw = ImageDraw.Draw(image)
        step = max(8, min(size) // 24)
        for y in range(0, size[1], step):
            for x in range(0, size[0], step):
                if (x // step + y // step) % 2 == 0:
                    shade = tuple(max(0, c - 55) for c in color)
                    draw.rectangle([x, y, x + step - 1, y + step - 1], fill=shade)
    buffer = BytesIO()
    image.save(buffer, format=fmt)
    content_type = {"PNG": "image/png", "WEBP": "image/webp"}.get(fmt, "image/jpeg")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=content_type)


class EagerCeleryMixin:
    """Run Celery tasks synchronously inside tests (no broker/worker needed)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from config.celery import app

        # The app reads Django settings with the CELERY_ namespace, so the
        # prefixed keys are the ones that take effect.
        cls._celery_app = app
        cls._celery_previous = (app.conf.task_always_eager, app.conf.task_eager_propagates)
        app.conf.CELERY_TASK_ALWAYS_EAGER = True
        # Tasks catch their own errors; not propagating lets Celery handle
        # its internal Retry signal the way a real worker does.
        app.conf.CELERY_TASK_EAGER_PROPAGATES = False

    @classmethod
    def tearDownClass(cls):
        eager, propagates = cls._celery_previous
        cls._celery_app.conf.CELERY_TASK_ALWAYS_EAGER = eager
        cls._celery_app.conf.CELERY_TASK_EAGER_PROPAGATES = propagates
        super().tearDownClass()


def tryon_settings(**overrides):
    """override_settings for a few keys of the TRYON dict (keeps all other keys)."""
    from django.conf import settings

    return override_settings(TRYON={**settings.TRYON, **overrides})
