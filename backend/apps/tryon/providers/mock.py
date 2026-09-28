"""
A fake engine for development, automated tests and demoing the app flow
without a GPU. It pastes the garment over the matching body region of the
photo. It is NOT a real try-on and must never be used in production.
"""
import time
from io import BytesIO

from django.conf import settings
from PIL import Image, ImageDraw

from .base import ProviderError, TryOnProvider, TryOnRequest, TryOnResult

# Fraction of the photo (left, top, right, bottom) covered per category
_REGIONS = {
    "upper_body": (0.22, 0.18, 0.78, 0.55),
    "lower_body": (0.25, 0.50, 0.75, 0.92),
    "dresses": (0.22, 0.18, 0.78, 0.90),
}


class MockProvider(TryOnProvider):
    name = "mock"

    def generate(self, request: TryOnRequest) -> TryOnResult:
        if request.category not in _REGIONS:
            raise ProviderError(f"Mock provider does not support '{request.category}'", retryable=False)
        started = time.monotonic()
        delay = settings.TRYON.get("MOCK_DELAY_SECONDS", 0)
        if delay:
            time.sleep(delay)

        person = Image.open(BytesIO(request.person_image)).convert("RGB")
        garment = Image.open(BytesIO(request.garment_image)).convert("RGBA")
        l, t, r, b = _REGIONS[request.category]
        box = (int(l * person.width), int(t * person.height), int(r * person.width), int(b * person.height))
        size = (box[2] - box[0], box[3] - box[1])
        garment = garment.resize(size)
        garment.putalpha(210)
        person.paste(garment, box[:2], garment)
        ImageDraw.Draw(person).rectangle(box, outline=(31, 56, 100), width=3)

        out = BytesIO()
        person.save(out, format="JPEG", quality=88)
        return TryOnResult(image=out.getvalue(), extension="jpg", inference_seconds=time.monotonic() - started)
