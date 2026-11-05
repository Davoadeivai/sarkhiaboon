"""
Django settings for the Sarkhiaboon backend.

Every environment-specific or secret value is read from environment variables.
See `.env.example` at the project root for the full list.
"""
import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env(name, default=None):
    return os.environ.get(name, default)


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name, default):
    value = os.environ.get(name)
    return int(value) if value not in (None, "") else default


def env_list(name, default=""):
    value = os.environ.get(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
DEBUG = env_bool("DJANGO_DEBUG", False)
SECRET_KEY = env("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "insecure-dev-only-key-change-me"
    else:
        raise RuntimeError("DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is off.")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", "")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third party
    "rest_framework",
    "rest_framework_simplejwt",
    "django_filters",
    "corsheaders",
    "drf_spectacular",
    # project apps
    "apps.core",
    "apps.accounts",
    "apps.catalog",
    "apps.tryon",
    "apps.orders",
    "apps.notifications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ---------------------------------------------------------------------------
# Database: PostgreSQL when POSTGRES_DB is set, otherwise SQLite for local dev
# ---------------------------------------------------------------------------
if env("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("POSTGRES_DB"),
            "USER": env("POSTGRES_USER", "postgres"),
            "PASSWORD": env("POSTGRES_PASSWORD", ""),
            "HOST": env("POSTGRES_HOST", "localhost"),
            "PORT": env("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": 60,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_USER_MODEL = "accounts.User"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

# ---------------------------------------------------------------------------
# Locale
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "fa-ir"
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static and media files
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(env("MEDIA_ROOT", str(BASE_DIR / "media")))

# Absolute base URL used when returning result image links to the app,
# e.g. https://api.sarkhiaboon.ir . Left empty, relative URLs are built
# from the incoming request.
PUBLIC_BASE_URL = env("PUBLIC_BASE_URL", "")

# ---------------------------------------------------------------------------
# CORS (the mobile app does not need it; a future web panel will)
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "")

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.DefaultPagination",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_RATES": {
        "otp_request": env("THROTTLE_OTP_REQUEST", "5/hour"),
        "otp_verify": env("THROTTLE_OTP_VERIFY", "20/hour"),
        "guest_login": env("THROTTLE_GUEST_LOGIN", "10/hour"),
    },
    "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
    # Behind nginx set TRUSTED_PROXY_COUNT=1 so throttling keys on the real
    # client IP (last X-Forwarded-For hop) and a client cannot spoof it.
    "NUM_PROXIES": env_int("TRUSTED_PROXY_COUNT", 0) or None,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env_int("JWT_ACCESS_MINUTES", 60)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env_int("JWT_REFRESH_DAYS", 30)),
    "ROTATE_REFRESH_TOKENS": True,
    "UPDATE_LAST_LOGIN": True,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Sarkhiaboon API",
    "DESCRIPTION": "API اپلیکیشن پرو مجازی لباس سرخیابون",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# ---------------------------------------------------------------------------
# Cache (used for throttling). Redis in production, local memory otherwise.
# ---------------------------------------------------------------------------
REDIS_URL = env("REDIS_URL", "")
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
        }
    }
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", REDIS_URL or "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = None
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", False)
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    "purge-expired-person-images": {
        "task": "apps.tryon.tasks.purge_expired_person_images",
        "schedule": 60 * 30,  # every 30 minutes
    },
    "expire-stale-tryon-jobs": {
        "task": "apps.tryon.tasks.expire_stale_jobs",
        "schedule": 60 * 5,
    },
    "release-unpaid-orders": {
        "task": "apps.orders.tasks.release_unpaid_orders",
        "schedule": 60 * 10,
    },
}

# ---------------------------------------------------------------------------
# SMS (OTP delivery)
# ---------------------------------------------------------------------------
SMS_BACKEND = env("SMS_BACKEND", "apps.accounts.sms.ConsoleSMSBackend")
KAVENEGAR_API_KEY = env("KAVENEGAR_API_KEY", "")
KAVENEGAR_OTP_TEMPLATE = env("KAVENEGAR_OTP_TEMPLATE", "verify")

OTP_LENGTH = env_int("OTP_LENGTH", 5)
OTP_TTL_SECONDS = env_int("OTP_TTL_SECONDS", 120)
OTP_MAX_ATTEMPTS = env_int("OTP_MAX_ATTEMPTS", 5)
OTP_RESEND_COOLDOWN_SECONDS = env_int("OTP_RESEND_COOLDOWN_SECONDS", 60)

# ---------------------------------------------------------------------------
# Virtual try-on engine
# ---------------------------------------------------------------------------
TRYON = {
    # Dotted path of the provider class. Swap engines by changing this only.
    "PROVIDER": env("TRYON_PROVIDER", "apps.tryon.providers.mock.MockProvider"),
    "RUNPOD_ENDPOINT_ID": env("RUNPOD_ENDPOINT_ID", ""),
    "RUNPOD_API_KEY": env("RUNPOD_API_KEY", ""),
    "RUNPOD_BASE_URL": env("RUNPOD_BASE_URL", "https://api.runpod.ai/v2"),
    "RUNPOD_POLL_INTERVAL_SECONDS": env_int("RUNPOD_POLL_INTERVAL_SECONDS", 2),
    "PROVIDER_TIMEOUT_SECONDS": env_int("TRYON_PROVIDER_TIMEOUT_SECONDS", 180),
    "MAX_RETRIES": env_int("TRYON_MAX_RETRIES", 2),
    "MOCK_DELAY_SECONDS": float(env("TRYON_MOCK_DELAY_SECONDS", "0")),
    # Input validation (rejects photos that would waste a paid GPU call)
    "MAX_UPLOAD_MB": env_int("TRYON_MAX_UPLOAD_MB", 8),
    "MIN_WIDTH": env_int("TRYON_MIN_WIDTH", 384),
    "MIN_HEIGHT": env_int("TRYON_MIN_HEIGHT", 512),
    "MAX_SIDE": env_int("TRYON_MAX_SIDE", 1536),
    "MIN_BRIGHTNESS": env_int("TRYON_MIN_BRIGHTNESS", 35),
    "MAX_BRIGHTNESS": env_int("TRYON_MAX_BRIGHTNESS", 235),
    # Edge-variance sharpness score; 0 disables the blur check.
    # Needs calibration against real customer photos before launch.
    "MIN_SHARPNESS": env_int("TRYON_MIN_SHARPNESS", 15),
    # Cost control
    "GUEST_DAILY_LIMIT": env_int("TRYON_GUEST_DAILY_LIMIT", 3),
    "USER_DAILY_LIMIT": env_int("TRYON_USER_DAILY_LIMIT", 30),
    "ENABLE_RESULT_CACHE": env_bool("TRYON_ENABLE_RESULT_CACHE", True),
    # Privacy: uploaded person photos are deleted this many hours after
    # upload. 0 = delete as soon as the try-on that used it has finished.
    "PERSON_PHOTO_RETENTION_HOURS": env_int("TRYON_PERSON_PHOTO_RETENTION_HOURS", 24),
    # Optional brand watermark (path to a PNG with transparency) on results
    "WATERMARK_IMAGE": env("TRYON_WATERMARK_IMAGE", ""),
    # Jobs stuck in the queue longer than this are marked failed
    "STALE_JOB_MINUTES": env_int("TRYON_STALE_JOB_MINUTES", 15),
}

# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Push notifications (swappable: LogPushBackend in development)
# ---------------------------------------------------------------------------
PUSH_BACKEND = env("PUSH_BACKEND", "apps.notifications.backends.LogPushBackend")
EXPO_PUSH_ACCESS_TOKEN = env("EXPO_PUSH_ACCESS_TOKEN", "")

PAYMENT_GATEWAY = env("PAYMENT_GATEWAY", "apps.orders.gateways.SandboxGateway")
ZARINPAL_MERCHANT_ID = env("ZARINPAL_MERCHANT_ID", "")
ZARINPAL_SANDBOX = env_bool("ZARINPAL_SANDBOX", True)
# Leave empty to build it from the request host
PAYMENT_CALLBACK_URL = env("PAYMENT_CALLBACK_URL", "")
# Unpaid orders release their reserved stock after this many minutes
ORDER_PAYMENT_TIMEOUT_MINUTES = env_int("ORDER_PAYMENT_TIMEOUT_MINUTES", 30)
# Shipping (Toman). Free above the threshold; 0 disables free shipping.
ORDER_SHIPPING_COST = env_int("ORDER_SHIPPING_COST", 0)
ORDER_FREE_SHIPPING_OVER = env_int("ORDER_FREE_SHIPPING_OVER", 0)
ORDER_MAX_QUANTITY_PER_ITEM = env_int("ORDER_MAX_QUANTITY_PER_ITEM", 10)
# After payment the browser is sent back to the app through this deep link
PAYMENT_RESULT_URL = env("PAYMENT_RESULT_URL", "sarkhiaboon://payment/result")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
}

# ---------------------------------------------------------------------------
# Production hardening (only when DEBUG is off)
# ---------------------------------------------------------------------------
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    # Usually the reverse proxy (nginx) redirects to HTTPS; enable here if not.
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", False)
    # HSTS is hard to undo once browsers cache it: enable only after HTTPS is
    # confirmed working on the final domain (e.g. 31536000 = one year).
    SECURE_HSTS_SECONDS = env_int("DJANGO_HSTS_SECONDS", 0)
