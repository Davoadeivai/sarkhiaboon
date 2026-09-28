from django.conf import settings


def absolute_media_url(file_field, request=None):
    """
    Build a full URL for a stored file so the mobile app can load it directly.
    Uses PUBLIC_BASE_URL when configured (production behind a proxy/CDN),
    otherwise the host of the incoming request.
    """
    if not file_field:
        return None
    url = file_field.url
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if settings.PUBLIC_BASE_URL:
        return settings.PUBLIC_BASE_URL.rstrip("/") + url
    if request is not None:
        return request.build_absolute_uri(url)
    return url
