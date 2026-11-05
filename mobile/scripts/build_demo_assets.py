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


def jpeg(cf, size=None, quality=84) -> str:
    img = Image.open(BytesIO(cf.read())).convert("RGB")
    if size:
        img = img.resize(size, Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return uri(buf.getvalue(), "image/jpeg")


def cutout(colour, shape, style=0, size=(450, 600)) -> str:
    """The garment alone on a transparent background, for compositing onto the shopper's photo."""
    w, h = size[0] * 2, size[1] * 2
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    seed._silhouette(ImageDraw.Draw(img), w, h, colour, shape, style)
    img = img.resize(size, Image.LANCZOS)
    img = img.crop(img.getbbox())
    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return uri(buf.getvalue(), "image/png")


shops = []
for sid, (name, city, colour, about) in enumerate(seed.SHOPS, start=1):
    shops.append({
        "id": sid, "name": name, "slug": f"shop-{sid}", "city": city, "description": about,
        "logo": content_png(seed._logo(colour, name[0]), (128, 128)),
        "cover": jpeg(seed._banner((900, 360), colour, name, f"فروشگاه ثبت‌شده در {city}")),
    })

categories, by_name = [], {}
cid = 0
for order, (name, tryon_type, colour, shape, children) in enumerate(seed.CATEGORIES):
    cid += 1
    top = {"id": cid, "name": name, "slug": f"cat-{cid}", "parent_id": None, "tryon_type": str(tryon_type),
           "image": jpeg(seed._png((300, 366), colour, shape, background=seed._tint(colour, 0.8))), "icon": None}
    categories.append(top)
    by_name[name] = (top, colour, shape)
    for k, (child_name, child_colour) in enumerate(children):
        cid += 1
        child = {"id": cid, "name": child_name, "slug": f"cat-{cid}", "parent_id": top["id"], "tryon_type": str(tryon_type),
                 "image": jpeg(seed._png((300, 366), child_colour, shape, style=k % 4, background=seed._tint(child_colour, 0.82))),
                 "icon": None}
        categories.append(child)
        by_name[child_name] = (child, child_colour, shape)

products = []
pid = 0
for cat_name, items in seed.PRODUCTS.items():
    cat, colour, shape = by_name[cat_name]
    for k, (pname, price, before) in enumerate(items):
        tone = seed._shade(colour, (0.85, 1.0, 1.15)[k % 3])
        products.append({
            "id": pid + 1, "name": pname, "slug": f"p-{pid + 1}", "price": price, "compare_at_price": before,
            "category_id": cat["id"], "shop_id": shops[(pid) % len(shops)]["id"], "tryon_type": cat["tryon_type"],
            "image": jpeg(seed._png((450, 600), tone, shape, style=k % 4)),
            "garment": cutout(tone, shape, k % 4) if shape in ("top", "pants", "coat") else None,
        })
        pid += 1

banners = []


def add_banner(position, title, subtitle, colour, link=None, page=None):
    banners.append({
        "id": len(banners) + 1, "title": title, "position": position, "placement": page,
        "image": jpeg(seed._banner((900, 450), colour, title, subtitle)),
        "link": {"type": "category", "slug": link} if link else {"type": "none"},
    })


manto = by_name["مانتو"][0]["slug"]
for title, sub, colour, link in [("حراج پاییزه", "تا ۳۰٪ تخفیف روی مانتو", (179, 38, 30), manto),
                                 ("اول پرو کن، بعد بخر", "لباس را روی عکس خودت ببین", (14, 124, 123), manto),
                                 ("کالکشن مجلسی", "مانتوهای تازه برای مهمانی", (52, 50, 84), by_name["مانتو مجلسی"][0]["slug"])]:
    add_banner("home_top", title, sub, colour, link)
for title, sub, colour in [("ارسال رایگان", "برای خرید بالای ۱ میلیون تومان", (46, 58, 98)),
                           ("جای تبلیغ شما", "برای رزرو این جایگاه با ما در تماس باشید", (150, 98, 66)),
                           ("فروشگاه‌های تازه", "بوتیک‌های جدید به سرخیابون پیوستند", (128, 36, 58))]:
    add_banner("home_middle", title, sub, colour)
pages = [("مانتو", by_name["مانتو"][0]["slug"], (118, 134, 98))] + [
    (n, by_name[n][0]["slug"], by_name[n][1]) for n, _ in seed.CATEGORIES[0][4]
]
for page_name, slug, colour in pages:
    for i, (title, sub) in enumerate([(page_name, "جدیدترین مدل‌ها از فروشگاه‌های ثبت‌شده"),
                                      ("تخفیف ویژه", f"{page_name} با قیمت استثنایی"),
                                      ("پرو مجازی", "قبل از خرید روی عکس خودت امتحان کن")]):
        add_banner("category_top", title, sub, seed._shade(colour, (1.0, 0.8, 0.65)[i]), page=slug)
for title, sub, colour in [("تا تصویرت آماده شود…", "مانتوهای پاییزه‌ی بوتیک لاله را ببین", (179, 38, 30)),
                           ("جای تبلیغ شما", "اینجا هر روز هزاران نفر منتظر پرو هستند", (52, 50, 84)),
                           ("پروی بیشتر", "با ورود با شماره موبایل، سهمیه‌ی روزانه‌ات بیشتر می‌شود", (14, 124, 123))]:
    add_banner("tryon_wait", title, sub, colour)


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
    f"export const DEMO_SHOPS = {json.dumps(shops, ensure_ascii=False)};\n"
    f"export const DEMO_PRODUCTS = {json.dumps(products, ensure_ascii=False)};\n"
    f"export const DEMO_BANNERS = {json.dumps(banners, ensure_ascii=False)};\n"
    f"export const DEMO_FONTS: Record<string, string> = {json.dumps(font_uris)};\n"
    f"export const DEMO_PERSON = {json.dumps(sample_person())};\n",
    encoding="utf-8",
)
print(f"wrote {out} ({out.stat().st_size // 1024} KB): {len(products)} products, {len(categories)} categories, {len(shops)} shops, {len(banners)} banners")
