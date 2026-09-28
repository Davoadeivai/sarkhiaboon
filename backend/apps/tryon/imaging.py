"""
Image checks and normalization for try-on photos.

Every photo is checked *before* it is sent to the (paid) GPU, so bad photos
are rejected for free with a helpful message instead of producing a bad result.
"""
import hashlib
from dataclasses import dataclass
from io import BytesIO

from django.conf import settings
from PIL import Image, ImageFilter, ImageOps, ImageStat, UnidentifiedImageError

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


class PhotoRejected(Exception):
    """Carries a Persian, user-facing reason."""


@dataclass
class NormalizedPhoto:
    data: bytes
    width: int
    height: int
    content_hash: str


def sharpness_score(image):
    """Variance of an edge map; low values mean a blurry or featureless photo."""
    gray = image.convert("L")
    gray.thumbnail((512, 512))
    edges = gray.filter(ImageFilter.FIND_EDGES)
    # The filter marks the photo's own border as an edge; crop it off.
    edges = edges.crop((2, 2, max(3, edges.width - 2), max(3, edges.height - 2)))
    return ImageStat.Stat(edges).var[0]


def normalize_person_photo(uploaded_file):
    """
    Validate an uploaded customer photo and return a clean JPEG version.

    - rejects oversized files, non-images, unsupported formats
    - applies the camera's EXIF rotation, then strips all EXIF metadata
      (phones embed GPS location; it must not be stored)
    - rejects photos that are too small, too dark, too bright or too blurry
    - downsizes very large photos to limit GPU cost and upload time
    """
    cfg = settings.TRYON
    max_bytes = cfg["MAX_UPLOAD_MB"] * 1024 * 1024
    if uploaded_file.size > max_bytes:
        raise PhotoRejected(f"حجم عکس بیشتر از {cfg['MAX_UPLOAD_MB']} مگابایت است.")

    raw = uploaded_file.read()
    try:
        probe = Image.open(BytesIO(raw))
        probe.verify()  # detects truncated/corrupt files
        image = Image.open(BytesIO(raw))
        image_format = image.format
        image.load()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise PhotoRejected("فایل ارسالی یک تصویر معتبر نیست.")
    if image_format not in ALLOWED_FORMATS:
        raise PhotoRejected("فقط عکس با فرمت JPG، PNG یا WEBP قابل قبول است.")

    image = ImageOps.exif_transpose(image).convert("RGB")
    width, height = image.size
    if width < cfg["MIN_WIDTH"] or height < cfg["MIN_HEIGHT"]:
        raise PhotoRejected(
            f"کیفیت عکس پایین است. حداقل ابعاد {cfg['MIN_WIDTH']}×{cfg['MIN_HEIGHT']} پیکسل لازم است."
        )
    if width > height * 1.2:
        raise PhotoRejected("لطفاً عکس را عمودی (ایستاده) بگیرید تا تمام قد شما دیده شود.")

    brightness = ImageStat.Stat(image.convert("L")).mean[0]
    if brightness < cfg["MIN_BRIGHTNESS"]:
        raise PhotoRejected("عکس خیلی تاریک است. لطفاً در نور بیشتری عکس بگیرید.")
    if brightness > cfg["MAX_BRIGHTNESS"]:
        raise PhotoRejected("عکس بیش از حد روشن است. لطفاً از نور مستقیم فاصله بگیرید.")
    if cfg["MIN_SHARPNESS"] and sharpness_score(image) < cfg["MIN_SHARPNESS"]:
        raise PhotoRejected("عکس تار است. لطفاً گوشی را ثابت نگه دارید و دوباره عکس بگیرید.")

    if max(image.size) > cfg["MAX_SIDE"]:
        image.thumbnail((cfg["MAX_SIDE"], cfg["MAX_SIDE"]), Image.LANCZOS)

    out = BytesIO()
    image.save(out, format="JPEG", quality=90, optimize=True)  # re-encoding drops all EXIF
    data = out.getvalue()
    return NormalizedPhoto(data=data, width=image.width, height=image.height, content_hash=hashlib.sha256(data).hexdigest())


def file_sha256(field_file):
    digest = hashlib.sha256()
    field_file.open("rb")
    try:
        for chunk in field_file.chunks():
            digest.update(chunk)
    finally:
        field_file.close()
    return digest.hexdigest()


def read_file_bytes(field_file):
    field_file.open("rb")
    try:
        return field_file.read()
    finally:
        field_file.close()


def apply_watermark(image_bytes):
    """Stamp the brand logo (TRYON['WATERMARK_IMAGE']) in the bottom corner, if configured."""
    path = settings.TRYON.get("WATERMARK_IMAGE")
    if not path:
        return image_bytes, None
    base = Image.open(BytesIO(image_bytes)).convert("RGBA")
    logo = Image.open(path).convert("RGBA")
    target_width = max(48, base.width // 6)
    logo = logo.resize((target_width, int(logo.height * target_width / logo.width)), Image.LANCZOS)
    alpha = logo.getchannel("A").point(lambda a: int(a * 0.6))
    logo.putalpha(alpha)
    margin = base.width // 40
    base.alpha_composite(logo, (margin, base.height - logo.height - margin))
    out = BytesIO()
    base.convert("RGB").save(out, format="JPEG", quality=92)
    return out.getvalue(), "jpg"
