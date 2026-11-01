"""
Fill an empty database with sample data for demos and app development:
    python manage.py seed_demo            (add sample data)
    python manage.py seed_demo --reset    (remove earlier sample data first)

All sample images are generated simple shapes, clearly not real products.
"""
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from PIL import Image, ImageDraw

from apps.catalog.models import Banner, Category, HomeShortcut, Product, ProductVariant, TryOnType

DEMO_TAG = "[نمونه]"

CATEGORIES = [
    # name, try-on type, colour, silhouette
    ("بلوز و شومیز", TryOnType.UPPER_BODY, (186, 118, 120), "top"),
    ("تیشرت", TryOnType.UPPER_BODY, (84, 116, 156), "top"),
    ("شلوار", TryOnType.LOWER_BODY, (52, 66, 104), "pants"),
    ("مانتو", TryOnType.DRESSES, (118, 134, 98), "coat"),
    ("کفش", TryOnType.SHOES, (150, 98, 66), "shoe"),
    ("کیف و اکسسوری", TryOnType.NONE, (186, 146, 66), "bag"),
]

PRODUCTS = {
    "بلوز و شومیز": [("شومیز حریر", 690_000, None), ("بلوز یقه‌گرد", 520_000, 650_000)],
    "تیشرت": [("تیشرت نخی ساده", 390_000, None), ("تیشرت اورسایز", 450_000, 560_000)],
    "شلوار": [("شلوار جین راسته", 980_000, None), ("شلوار پارچه‌ای", 760_000, None)],
    "مانتو": [("مانتو کتان بلند", 1_450_000, 1_800_000), ("مانتو جلوباز", 1_200_000, None)],
    "کفش": [("کتانی سفید", 1_650_000, None)],
    "کیف و اکسسوری": [("کیف دوشی چرم", 1_100_000, None)],
}

SS = 2  # draw at 2x and downsample for smooth edges


def _shade(colour, k):
    return tuple(max(0, min(255, int(c * k))) for c in colour)


def _silhouette(draw, w, h, colour, shape):
    """Simple flat garment drawings, clearly placeholders rather than real products."""
    dark = _shade(colour, 0.82)
    if shape == "top":
        body = [(w * .32, h * .16), (w * .68, h * .16), (w * .9, h * .33), (w * .8, h * .42), (w * .74, h * .37),
                (w * .74, h * .84), (w * .26, h * .84), (w * .26, h * .37), (w * .2, h * .42), (w * .1, h * .33)]
        draw.polygon(body, fill=colour)
        draw.chord([w * .41, h * .1, w * .59, h * .22], 0, 180, fill=_shade((236, 238, 243), 1))
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
        draw.polygon([(w * .42, h * .1), (w * .5, h * .3), (w * .58, h * .1)], fill=(236, 238, 243))
    elif shape == "shoe":
        draw.polygon([(w * .14, h * .62), (w * .4, h * .48), (w * .56, h * .5), (w * .86, h * .64), (w * .86, h * .72),
                      (w * .14, h * .72)], fill=colour)
        draw.rectangle([w * .14, h * .72, w * .86, h * .76], fill=(250, 250, 250))
    else:  # bag
        draw.arc([w * .34, h * .22, w * .66, h * .52], 180, 360, fill=dark, width=int(w * .03))
        draw.rounded_rectangle([w * .22, h * .38, w * .78, h * .8], radius=w * .05, fill=colour)
        draw.rectangle([w * .22, h * .38, w * .78, h * .48], fill=dark)


def _png(size, colour, shape="top"):
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
            mix = 0.1 + 0.07 * k  # blend towards white: quiet, tone-on-tone arches
            tone = tuple(int(c + (255 - c) * mix) for c in _shade(colour, 0.95))
            draw.rounded_rectangle([x, h * .22, x + aw, h * 1.05], radius=aw / 2, fill=tone)
    else:
        image = Image.new("RGB", (w, h), (236, 238, 243))
        draw = ImageDraw.Draw(image)
        for i in range(h):
            draw.line([(0, i), (w, i)], fill=_shade((240, 242, 246), 1 - 0.06 * i / h))
        _silhouette(draw, w, h, colour, shape)
    image = image.resize(size, Image.LANCZOS)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return ContentFile(buffer.getvalue())


class Command(BaseCommand):
    help = "Create sample categories, products, banners and home icons (for demos)."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete previously seeded sample data first.")

    @transaction.atomic
    def handle(self, *args, reset=False, **options):
        if reset:
            Product.objects.filter(name__startswith=DEMO_TAG).delete()
            Banner.objects.filter(title__startswith=DEMO_TAG).delete()
            HomeShortcut.objects.filter(title__startswith=DEMO_TAG).delete()
            Category.objects.filter(name__startswith=DEMO_TAG).delete()

        if Category.objects.filter(name__startswith=DEMO_TAG).exists():
            self.stdout.write(self.style.WARNING("Sample data already exists. Use --reset to recreate it."))
            return

        categories = {}
        for order, (name, tryon_type, colour, shape) in enumerate(CATEGORIES):
            category = Category(name=f"{DEMO_TAG} {name}", tryon_type=tryon_type, show_on_home=True, order=order)
            category.icon.save("icon.png", _png((128, 128), colour, "icon"), save=False)
            category.save()
            categories[name] = (category, colour, shape)

        count = 0
        for cat_name, items in PRODUCTS.items():
            category, colour, shape = categories[cat_name]
            for name, price, before in items:
                product = Product(name=f"{DEMO_TAG} {name}", category=category, price=price, compare_at_price=before,
                                  description="محصول نمونه برای نمایش و توسعه‌ی اپلیکیشن.")
                product.image.save("product.png", _png((600, 800), colour, shape), save=False)
                product.save()
                for size, stock in (("S", 5), ("M", 8), ("L", 3)):
                    ProductVariant.objects.create(product=product, size=size, color="پیش‌فرض", stock=stock)
                count += 1

        first = Product.objects.filter(name__startswith=DEMO_TAG).order_by("pk").first()
        banner = Banner(title=f"{DEMO_TAG} حراج پاییزه", position=Banner.Position.HOME_TOP,
                        link_type=Banner.LinkType.CATEGORY, category=categories["مانتو"][0])
        banner.image.save("banner.png", _png((1200, 600), (14, 124, 123), "banner"), save=False)
        banner.save()
        banner2 = Banner(title=f"{DEMO_TAG} پرو مجازی را امتحان کنید", position=Banner.Position.HOME_MIDDLE,
                         link_type=Banner.LinkType.PRODUCT, product=first)
        banner2.image.save("banner.png", _png((1200, 600), (52, 50, 84), "banner"), save=False)
        banner2.save()

        for order, (title, colour, shape) in enumerate((("تخفیف‌ها", (227, 162, 43), "icon"), ("جدیدترین‌ها", (52, 66, 104), "icon"),
                                                         ("پرو مجازی", (14, 124, 123), "arch-icon"))):
            shortcut = HomeShortcut(title=f"{DEMO_TAG} {title}", order=order, link_type=HomeShortcut.LinkType.CATEGORY,
                                    category=categories["بلوز و شومیز"][0])
            shortcut.icon.save("icon.png", _png((128, 128), colour, shape), save=False)
            shortcut.save()

        self.stdout.write(self.style.SUCCESS(
            f"Created {len(categories)} categories, {count} products, 2 banners and 3 home icons."
        ))
