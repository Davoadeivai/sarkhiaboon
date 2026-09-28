"""Iranian mobile number normalization and validation."""
import re

from django.core.exceptions import ValidationError

_PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_MOBILE_RE = re.compile(r"^09\d{9}$")


def normalize_phone(raw):
    """
    Convert common input forms to the canonical 09XXXXXXXXX format.

    Accepts Persian/Arabic digits, spaces, dashes, and the +98 / 0098 / 98 prefixes.
    Raises ValidationError if the result is not a valid Iranian mobile number.
    """
    if raw is None:
        raise ValidationError("شماره موبایل وارد نشده است.")
    value = str(raw).translate(_PERSIAN_DIGITS)
    value = re.sub(r"[\s\-()]", "", value)
    if value.startswith("+98"):
        value = "0" + value[3:]
    elif value.startswith("0098"):
        value = "0" + value[4:]
    elif value.startswith("98") and len(value) == 12:
        value = "0" + value[2:]
    elif value.startswith("9") and len(value) == 10:
        value = "0" + value
    if not _MOBILE_RE.match(value):
        raise ValidationError("شماره موبایل معتبر نیست. نمونه‌ی صحیح: 09121234567")
    return value


def validate_phone(value):
    normalize_phone(value)
