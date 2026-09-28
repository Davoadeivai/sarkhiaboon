from functools import lru_cache

from django.conf import settings
from django.utils.module_loading import import_string

from .base import ProviderError, TryOnProvider, TryOnRequest, TryOnResult  # noqa: F401


@lru_cache(maxsize=4)
def _load(path):
    return import_string(path)()


def get_provider() -> TryOnProvider:
    """The configured try-on engine (settings.TRYON['PROVIDER'])."""
    return _load(settings.TRYON["PROVIDER"])


def available_tryon_types():
    """Try-on categories the active engine can handle (e.g. no shoes yet)."""
    return tuple(get_provider().supported_categories)
