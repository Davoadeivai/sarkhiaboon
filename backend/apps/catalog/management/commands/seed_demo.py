"""
Fill an empty database with sample data for demos and app development:
    python manage.py seed_demo            (add sample data)
    python manage.py seed_demo --reset    (remove earlier sample data first)

Creates the store layout the client asked for: clothing categories with photos,
«مانتو» with four subcategories (school, office, formal, casual), three
registered shops, and slider banners for the home page, every category page and
the try-on waiting screen.

All sample images are generated drawings, clearly not real products. Banner text
is drawn with the bundled OFL fonts when Pillow has Persian text shaping (raqm);
otherwise the banners are drawn without text.
"""
from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from PIL import Image, ImageDraw, ImageFont, features

from apps.catalog.models import Banner, Category, HomeShortcut, Product, ProductVariant, Shop, TryOnType

DEMO_TAG = "[نمونه]"
FONTS = Path(__file__).resolve().parent / "demo_fonts"
TEXT = features.check("raqm")

# name, try-on type, colour, silhouette, children [(name, colour)]
CATEGORIES = [
    ("مانتو", TryOnType.DRESSES, (118, 134, 98), "coat", [
        ("مانتو مدرسه", (46, 58, 98)),
        ("مانتو اداری", (74, 80, 92)),
        ("مانتو مجلسی", (128, 36, 58)),
        ("مانتو راحتی", (176, 150, 112)),
    ]),
    ("شومیز و بلوز", TryOnType.UPPER_BODY, (186, 118, 120), "top", []),
    ("تیشرت", TryOnType.UPPER_BODY, (84, 116, 156), "top", []),
    ("شلوار", TryOnType.LOWER_BODY, (52, 66, 104), "pants", []),
    ("کفش", TryOnType.SHOES, (150, 98, 66), "shoe", []),
    ("کیف و اکسسوری", TryOnType.NONE, (186, 146, 66), "bag", []),
]

# category name -> [(product name, price, compare-at price)]
PRODUCTS = {
    "مانتو مدرسه": [("مانتو مدرسه سرمه‌ای", 890_000, None), ("مانتو مدرسه کتان", 960_000, 1_150_000),
                    ("مانتو مدرسه ساده", 790_000, None)],
    "مانتو اداری": [("مانتو اداری کرپ", 1_350_000, None), ("مانتو اداری جیب‌دار", 1_480_000, 1_750_000),
                    ("مانتو اداری بلند", 1_590_000, None)],
    "مانتو مجلسی": [("مانتو مجلسی ساتن", 2_150_000, None), ("مانتو مجلسی گیپور", 2_480_000, 2_900_000),
                    ("مانتو مجلسی کمربنددار", 2_290_000, None)],
    "مانتو راحتی": [("مانتو راحتی نخی", 980_000, None), ("مانتو راحتی جلوباز", 1_120_000, 1_300_000),
                    ("مانتو راحتی کتان", 1_050_000, None)],
    "شومیز و بلوز": [("شومیز حریر", 690_000, None), ("بلوز یقه‌گرد", 520_000, 650_000)],
    "تیشرت": [("تیشرت نخی ساده", 390_000, None), ("تیشرت اورسایز", 450_000, 560_000)],
    "شلوار": [("شلوار جین راسته", 980_000, None), ("شلوار پارچه‌ای", 760_000, None)],
    "کفش": [("کتانی سفید", 1_650_000, None)],
    "کیف و اکسسوری": [("کیف دوشی چرم", 1_100_000, None)],
}

# name, city, colour, description
SHOPS = [
    ("بوتیک لاله", "تهران", (179, 38, 30), "مانتو و پوشاک روزمره، دوخت تهران."),
    ("مزون نگار", "اصفهان", (52, 50, 84), "مانتوهای مجلسی و اداری با پارچه‌ی درجه‌یک."),
    ("پوشاک آفتاب", "شیراز", (14, 124, 123), "پوشاک راحتی و نخی برای هر روز."),
]

SS = 2  # draw at 2x and downsample for smooth edges
BG = (236, 238, 243)


def _shade(colour, k):
    return tuple(max(0, min(255, int(c * k))) for c in colour)


def _tint(colour, mix):
    """Blend a colour towards white (0 = unchanged, 1 = white)."""
    return tuple(int(c + (255 - c) * mix) for c in colour)


def _silhouette(draw, w, h, colour, shape, style=0):
    """Simple flat garment drawings, clearly placeholders rather than real products."""
    dark = _shade(colour, 0.82)
    if shape == "top":
        body = [(w * .32, h * .16), (w * .68, h * .16), (w * .9, h * .33), (w * .8, h * .42), (w * .74, h * .37),
                (w * .74, h * .84), (w * .26, h * .84), (w * .26, h * .37), (w * .2, h * .42), (w * .1, h * .33)]
        draw.polygon(body, fill=colour)
        draw.chord([w * .41, h * .1, w * .59, h * .22], 0, 180, fill=BG)
        draw.polygon([(w * .5, h * .2), (w * .74, h * .37), (w * .74, h * .84), (w * .5, h * .84)], fill=dark)
    elif shape == "pants":
        draw.polygon([(w * .3, h * .12), (w * .7, h * .12), (w * .76, h * .88), (w * .56, h * .88), (w * .5, h * .38),
                      (w * .44, h * .88), (w * .24, h * .88)], fill=colour)
        draw.polygon([(w * .5, h * .12), (w * .7, h * .12), (w * .76, h * .88), (w * .56, h * .88), (w * .5, h * .38)], fill=dark)
        draw.rectangle([w * .3, h * .12, w * .7, h * .16], fill=_shade(colour, 0.7))
    elif shape == "coat":
        draw.polygon([(w * .34, h * .1), (w * .66, h * .1), (w * .86, h * .26), (w * .82, h * .62), (w * .74, h * .6),
                      (w * .78, h * .92), (w * .22, h * .92), (w * .26, h * .6), (w * .18, h * .62), (w * .14, h * .26)], fill=colour)
        draw.polygon([(w * .5, h * .18), (w * .66, h * .1), (w * .86, h * .26), (w * .82, h * .62), (w * .74, h * .6),
                      (w * .78, h * .92), (w * .5, h * .92)], fill=dark)
        draw.polygon([(w * .42, h * .1), (w * .5, h * .3), (w * .58, h * .1)], fill=BG)
        if style == 1:  # belt
            draw.rectangle([w * .25, h * .5, w * .75, h * .54], fill=_shade(colour, 0.6))
            draw.rectangle([w * .47, h * .495, w * .53, h * .545], fill=(214, 186, 120))
        elif style == 2:  # buttons
            for k in range(4):
                y = h * (.36 + .11 * k)
                draw.ellipse([w * .485, y, w * .515, y + w * .03], fill=_shade(colour, 0.55))
        elif style == 3:  # pockets
            draw.rectangle([w * .3, h * .64, w * .42, h * .72], outline=_shade(colour, 0.6), width=int(w * .01))
            draw.rectangle([w * .58, h * .64, w * .7, h * .72], outline=_shade(colour, 0.5), width=int(w * .01))
    elif shape == "shoe":
        draw.polygon([(w * .14, h * .62), (w * .4, h * .48), (w * .56, h * .5), (w * .86, h * .64), (w * .86, h * .72),
                      (w * .14, h * .72)], fill=colour)
        draw.rectangle([w * .14, h * .72, w * .86, h * .76], fill=(250, 250, 250))
    else:  # bag
        draw.arc([w * .34, h * .22, w * .66, h * .52], 180, 360, fill=dark, width=int(w * .03))
        draw.rounded_rectangle([w * .22, h * .38, w * .78, h * .8], radius=w * .05, fill=colour)
        draw.rectangle([w * .22, h * .38, w * .78, h * .48], fill=dark)


def _font(name, size):
    try:
        return ImageFont.truetype(str(FONTS / name), size, layout_engine=ImageFont.Layout.RAQM)
    except Exception:  # noqa: BLE001 - missing font or shaping library: draw without text
        return None


def _text_right(draw, xy_right, text, font, fill, max_width=None):
    """Right-aligned Persian text (raqm shapes and orders the letters), shrunk to fit max_width."""
    if not (TEXT and font):
        return
    width = draw.textlength(text, font=font, direction="rtl")
    while max_width and width > max_width and font.size > 12:
        font = font.font_variant(size=int(font.size * 0.92))
        width = draw.textlength(text, font=font, direction="rtl")
    draw.text((xy_right[0] - width, xy_right[1]), text, font=font, fill=fill, direction="rtl")


def _to_file(image, fmt="PNG"):
    buffer = BytesIO()
    image.save(buffer, format=fmt, quality=88) if fmt == "JPEG" else image.save(buffer, format=fmt)
    return ContentFile(buffer.getvalue())


def _png(size, colour, shape="top", style=0, background=BG):
    """Product photo stand-in, category tile, round icon or banner background."""
    w, h = size[0] * SS, size[1] * SS
    if shape in ("icon", "arch-icon"):
        image = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        if shape == "arch-icon":
            draw.rounded_rectangle([w * .26, h * .14, w * .74, h * .86], radius=w * .24, fill=colour)
            draw.rectangle([w * .26, h * .6, w * .74, h * .86], fill=colour)
        else:
            draw.ellipse([w * .18, h * .18, w * .82, h * .82], fill=colour)
    elif shape == "banner":
        image = Image.new("RGB", (w, h), colour)
        draw = ImageDraw.Draw(image)
        for i in range(h):  # soft vertical gradient
            draw.line([(0, i), (w, i)], fill=_shade(colour, 1.12 - 0.3 * i / h))
        aw = h * .62  # a row of arches, the app's motif
        for k, x in enumerate((w * .06, w * .06 + aw * 1.15, w * .06 + aw * 2.3)):
            draw.rounded_rectangle([x, h * .22, x + aw, h * 1.05], radius=aw / 2, fill=_tint(_shade(colour, 0.95), 0.1 + 0.07 * k))
    else:
        image = Image.new("RGB", (w, h), background)
        draw = ImageDraw.Draw(image)
        for i in range(h):
            draw.line([(0, i), (w, i)], fill=_shade(_tint(background, 0.25), 1 - 0.06 * i / h))
        _silhouette(draw, w, h, colour, shape, style)
    image = image.resize(size, Image.LANCZOS)
    return _to_file(image)


def _banner(size, colour, title, subtitle=""):
    """Slider banner: gradient, tone-on-tone arches, and Persian copy on the right."""
    w, h = size[0] * SS, size[1] * SS
    image = Image.open(_png(size, colour, "banner")).convert("RGB").resize((w, h))
    draw = ImageDraw.Draw(image)
    title_font = _font("Lalezar-Regular.ttf", int(h * .2))
    sub_font = _font("Vazirmatn-Medium.ttf", int(h * .085))
    _text_right(draw, (w * .93, h * .26), title, title_font, (255, 255, 255), max_width=w * .8)
    if subtitle:
        _text_right(draw, (w * .93, h * .56), subtitle, sub_font, _tint(colour, 0.78), max_width=w * .8)
    return _to_file(image.resize(size, Image.LANCZOS), "JPEG")


def _logo(colour, letter):
    w = 256 * SS
    image = Image.new("RGBA", (w, w), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse([0, 0, w - 1, w - 1], fill=colour)
    font = _font("Lalezar-Regular.ttf", int(w * .5))
    if TEXT and font:
        box = draw.textbbox((0, 0), letter, font=font, direction="rtl")
        draw.text(((w - (box[2] - box[0])) / 2 - box[0], (w - (box[3] - box[1])) / 2 - box[1]), letter,
                  font=font, fill=(255, 255, 255), direction="rtl")
    return _to_file(image.resize((256, 256), Image.LANCZOS))


class Command(BaseCommand):
    help = "Create sample categories, shops, products and banners (for demos)."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete previously seeded sample data first.")

    @transaction.atomic
    def handle(self, *args, reset=False, **options):
        if reset:
            Product.objects.filter(name__startswith=DEMO_TAG).delete()
            Banner.objects.filter(title__startswith=DEMO_TAG).delete()
            HomeShortcut.objects.filter(title__startswith=DEMO_TAG).delete()
            Category.objects.filter(name__startswith=DEMO_TAG, parent__isnull=False).delete()
            Category.objects.filter(name__startswith=DEMO_TAG).delete()
            Shop.objects.filter(name__startswith=DEMO_TAG).delete()

        if Category.objects.filter(name__startswith=DEMO_TAG).exists():
            self.stdout.write(self.style.WARNING("Sample data already exists. Use --reset to recreate it."))
            return

        shops = []
        for order, (name, city, colour, about) in enumerate(SHOPS):
            shop = Shop(name=f"{DEMO_TAG} {name}", city=city, description=about, order=order)
            shop.logo.save("logo.png", _logo(colour, name[0]), save=False)
            shop.cover.save("cover.jpg", _banner((1200, 480), colour, name, f"فروشگاه ثبت‌شده در {city}"), save=False)
            shop.save()
            shops.append(shop)

        cats = {}
        for order, (name, tryon_type, colour, shape, children) in enumerate(CATEGORIES):
            cat = Category(name=f"{DEMO_TAG} {name}", tryon_type=tryon_type, show_on_home=True, order=order)
            cat.icon.save("icon.png", _png((128, 128), colour, "icon"), save=False)
            cat.image.save("tile.png", _png((360, 440), colour, shape, background=_tint(colour, 0.8)), save=False)
            cat.save()
            cats[name] = (cat, colour, shape)
            for child_order, (child_name, child_colour) in enumerate(children):
                child = Category(name=f"{DEMO_TAG} {child_name}", parent=cat, tryon_type=tryon_type, order=child_order)
                child.image.save("tile.png", _png((360, 440), child_colour, shape, style=child_order % 4,
                                                  background=_tint(child_colour, 0.82)), save=False)
                child.save()
                cats[child_name] = (child, child_colour, shape)

        count = 0
        for cat_name, items in PRODUCTS.items():
            category, colour, shape = cats[cat_name]
            for k, (name, price, before) in enumerate(items):
                product = Product(
                    name=f"{DEMO_TAG} {name}", category=category, shop=shops[(count + k) % len(shops)],
                    price=price, compare_at_price=before,
                    description="محصول نمونه برای نمایش و توسعه‌ی اپلیکیشن. قبل از خرید، روی عکس خودت پرو کن.",
                )
                tone = _shade(colour, (0.85, 1.0, 1.15)[k % 3])
                product.image.save("product.png", _png((600, 800), tone, shape, style=k % 4), save=False)
                product.save()
                for size, stock in (("S", 5), ("M", 8), ("L", 3)):
                    ProductVariant.objects.create(product=product, size=size, color="پیش‌فرض", stock=stock)
                count += 1

        def banner(position, title, subtitle, colour, order, link=None, page=None):
            b = Banner(title=f"{DEMO_TAG} {title}", position=position, order=order, placement_category=page)
            if link is not None:
                b.link_type = Banner.LinkType.CATEGORY
                b.category = link
            b.image.save("banner.jpg", _banner((1200, 600), colour, title, subtitle), save=False)
            b.save()

        manto = cats["مانتو"][0]
        top = [("حراج پاییزه", "تا ۳۰٪ تخفیف روی مانتو", (179, 38, 30), manto),
               ("اول پرو کن، بعد بخر", "لباس را روی عکس خودت ببین", (14, 124, 123), manto),
               ("کالکشن مجلسی", "مانتوهای تازه برای مهمانی", (52, 50, 84), cats["مانتو مجلسی"][0])]
        for i, (title, sub, colour, link) in enumerate(top):
            banner(Banner.Position.HOME_TOP, title, sub, colour, i, link)
        middle = [("ارسال رایگان", "برای خرید بالای ۱ میلیون تومان", (46, 58, 98)),
                  ("جای تبلیغ شما", "برای رزرو این جایگاه با ما در تماس باشید", (150, 98, 66)),
                  ("فروشگاه‌های تازه", "بوتیک‌های جدید به سرخیابون پیوستند", (128, 36, 58))]
        for i, (title, sub, colour) in enumerate(middle):
            banner(Banner.Position.HOME_MIDDLE, title, sub, colour, i)
        pages = [("مانتو", manto, (118, 134, 98))] + [
            (name, cats[name][0], cats[name][1]) for name, _ in CATEGORIES[0][4]
        ]
        for page_name, page, colour in pages:
            slides = [(page_name, "جدیدترین مدل‌ها از فروشگاه‌های ثبت‌شده"),
                      ("تخفیف ویژه", f"{page_name} با قیمت استثنایی"),
                      ("پرو مجازی", "قبل از خرید روی عکس خودت امتحان کن")]
            for i, (title, sub) in enumerate(slides):
                banner(Banner.Position.CATEGORY_TOP, title, sub, _shade(colour, (1.0, 0.8, 0.65)[i]), i, page=page)
        wait = [("تا تصویرت آماده شود…", "مانتوهای پاییزه‌ی بوتیک لاله را ببین", (179, 38, 30)),
                ("جای تبلیغ شما", "اینجا هر روز هزاران نفر منتظر پرو هستند", (52, 50, 84)),
                ("پروی بیشتر", "با ورود با شماره موبایل، سهمیه‌ی روزانه‌ات بیشتر می‌شود", (14, 124, 123))]
        for i, (title, sub, colour) in enumerate(wait):
            banner(Banner.Position.TRYON_WAIT, title, sub, colour, i)

        self.stdout.write(self.style.SUCCESS(
            f"Created {len(cats)} categories, {len(shops)} shops, {count} products and "
            f"{Banner.objects.filter(title__startswith=DEMO_TAG).count()} banners."
            + ("" if TEXT else " (Banner text skipped: Pillow has no Persian text shaping.)")
        ))
