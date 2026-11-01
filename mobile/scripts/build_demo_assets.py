"""
Generate src/lib/demo/assets.generated.ts for the browser-only demo build.

Embeds (as data: URIs) the demo product images, garment cut-outs for the
simulated try-on, banners, promo icons and the four app fonts, so the demo
runs as one self-contained web page with no server.

    cd mobile && python scripts/build_demo_assets.py

Product drawings reuse the backend's seed_demo drawing code, so the demo looks
exactly like the development server's sample catalog.
"""
import base64
import json
import os
import sys
from io import BytesIO
from pathlib import Path

HERE = Path(__file__).resolve().parent
MOBILE = HERE.parent
BACKEND = MOBILE.parent / "backend"
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ.setdefault("DJANGO_DEBUG", "true")

import django  # noqa: E402

django.setup()

from PIL import Image, ImageDraw  # noqa: E402

from apps.catalog.management.commands import seed_demo as seed  # noqa: E402


def uri(data: bytes, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


def content_png(cf, size=None, quality=None) -> str:
    img = Image.open(BytesIO(cf.read()))
    if size:
        img = img.resize(size, Image.LANCZOS)
    buf = BytesIO()
    if quality:
        img.convert("RGB").save(buf, format="JPEG", quality=quality, optimize=True)
        return uri(buf.getvalue(), "image/jpeg")
    img.save(buf, format="PNG", optimize=True)
    return uri(buf.getvalue(), "image/png")


def cutout(colour, shape, size=(450, 600)) -> str:
    """The garment alone on a transparent background, for compositing onto the shopper's photo."""
    w, h = size[0] * 2, size[1] * 2
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    seed._silhouette(ImageDraw.Draw(img), w, h, colour, shape)
    img = img.resize(size, Image.LANCZOS)
    # Crop to the garment so the app can scale it onto the body region.
    img = img.crop(img.getbbox())
    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return uri(buf.getvalue(), "image/png")


categories = []
products = []
pid = 1
for cid, (name, tryon_type, colour, shape) in enumerate(seed.CATEGORIES, start=1):
    categories.append({
        "id": cid,
        "name": name,
        "slug": f"cat-{cid}",
        "tryon_type": str(tryon_type),
        "icon": content_png(seed._png((128, 128), colour, "icon"), (96, 96)),
    })
    for pname, price, before in seed.PRODUCTS[name]:
        products.append({
            "id": pid,
            "name": pname,
            "slug": f"p-{pid}",
            "price": price,
            "compare_at_price": before,
            "category_id": cid,
            "tryon_type": str(tryon_type),
            "image": content_png(seed._png((450, 600), colour, shape), quality=86),
            "garment": cutout(colour, shape) if shape in ("top", "pants", "coat") else None,
        })
        pid += 1

banners = [
    {"id": 1, "title": "حراج پاییزه", "position": "home_top",
     "image": content_png(seed._png((900, 450), (14, 124, 123), "banner"), quality=85),
     "link": {"type": "category", "slug": "cat-4"}},
    {"id": 2, "title": "پرو مجازی را امتحان کنید", "position": "home_middle",
     "image": content_png(seed._png((900, 450), (52, 50, 84), "banner"), quality=85),
     "link": {"type": "product", "slug": "p-1"}},
]
shortcuts = [
    {"id": 1, "title": "تخفیف‌ها", "icon": content_png(seed._png((128, 128), (227, 162, 43), "icon"), (96, 96)),
     "link": {"type": "category", "slug": "cat-2"}},
    {"id": 2, "title": "جدیدترین‌ها", "icon": content_png(seed._png((128, 128), (52, 66, 104), "icon"), (96, 96)),
     "link": {"type": "category", "slug": "cat-3"}},
    {"id": 3, "title": "پرو مجازی", "icon": content_png(seed._png((128, 128), (14, 124, 123), "arch-icon"), (96, 96)),
     "link": {"type": "category", "slug": "cat-4"}},
]

def sample_person() -> str:
    """An illustrated full-length figure, for trying the demo without your own photo."""
    import random
    random.seed(7)
    W, H = 600, 800
    img = Image.new("RGB", (W, H), (226, 228, 233))
    d = ImageDraw.Draw(img)
    for y in range(H):
        d.line([(0, y), (W, y)], fill=seed._shade((232, 234, 239), 1 - 0.08 * y / H))
    for _ in range(5000):  # wall texture
        x, y = random.randrange(W), random.randrange(H)
        c = random.randint(214, 236)
        d.point((x, y), fill=(c, c + 1, c + 4))
    skin, hair, shirt, pants = (205, 166, 140), (58, 44, 40), (238, 238, 236), (58, 62, 80)
    d.ellipse([W * .43, H * .07, W * .57, H * .2], fill=skin)
    d.ellipse([W * .42, H * .05, W * .58, H * .13], fill=hair)
    d.rectangle([W * .475, H * .19, W * .525, H * .235], fill=skin)
    d.polygon([(W * .33, H * .235), (W * .67, H * .235), (W * .7, H * .55), (W * .3, H * .55)], fill=shirt)
    d.polygon([(W * .33, H * .235), (W * .25, H * .5), (W * .29, H * .52), (W * .37, H * .32)], fill=shirt)
    d.polygon([(W * .67, H * .235), (W * .75, H * .5), (W * .71, H * .52), (W * .63, H * .32)], fill=shirt)
    d.ellipse([W * .245, H * .495, W * .295, H * .535], fill=skin)
    d.ellipse([W * .705, H * .495, W * .755, H * .535], fill=skin)
    d.polygon([(W * .31, H * .55), (W * .69, H * .55), (W * .66, H * .95), (W * .53, H * .95), (W * .5, H * .62),
               (W * .47, H * .95), (W * .34, H * .95)], fill=pants)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return uri(buf.getvalue(), "image/jpeg")


FONTS = MOBILE / "node_modules" / "@expo-google-fonts"
fonts = {
    "Lalezar_400Regular": FONTS / "lalezar/400Regular/Lalezar_400Regular.ttf",
    "Vazirmatn_400Regular": FONTS / "vazirmatn/400Regular/Vazirmatn_400Regular.ttf",
    "Vazirmatn_500Medium": FONTS / "vazirmatn/500Medium/Vazirmatn_500Medium.ttf",
    "Vazirmatn_700Bold": FONTS / "vazirmatn/700Bold/Vazirmatn_700Bold.ttf",
}
font_uris = {k: uri(p.read_bytes(), "font/ttf") for k, p in fonts.items()}

out = MOBILE / "src/lib/demo/assets.generated.ts"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(
    "// Generated by scripts/build_demo_assets.py — do not edit.\n"
    "/* eslint-disable */\n"
    f"export const DEMO_CATEGORIES = {json.dumps(categories, ensure_ascii=False)};\n"
    f"export const DEMO_PRODUCTS = {json.dumps(products, ensure_ascii=False)};\n"
    f"export const DEMO_BANNERS = {json.dumps(banners, ensure_ascii=False)};\n"
    f"export const DEMO_SHORTCUTS = {json.dumps(shortcuts, ensure_ascii=False)};\n"
    f"export const DEMO_FONTS: Record<string, string> = {json.dumps(font_uris)};\n"
    f"export const DEMO_PERSON = {json.dumps(sample_person())};\n",
    encoding="utf-8",
)
print(f"wrote {out} ({out.stat().st_size // 1024} KB): {len(products)} products, {len(categories)} categories")
