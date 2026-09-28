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
    # name, try-on type, colour
    ("بلوز و شومیز", TryOnType.UPPER_BODY, (196, 84, 84)),
    ("تیشرت", TryOnType.UPPER_BODY, (70, 110, 170)),
    ("شلوار", TryOnType.LOWER_BODY, (60, 60, 90)),
    ("مانتو", TryOnType.DRESSES, (120, 150, 110)),
    ("کفش", TryOnType.SHOES, (140, 100, 70)),
    ("کیف و اکسسوری", TryOnType.NONE, (180, 150, 60)),
]

PRODUCTS = {
    "بلوز و شومیز": [("شومیز حریر", 690_000, None), ("بلوز یقه‌گرد", 520_000, 650_000)],
    "تیشرت": [("تیشرت نخی ساده", 390_000, None), ("تیشرت اورسایز", 450_000, 560_000)],
    "شلوار": [("شلوار جین راسته", 980_000, None), ("شلوار پارچه‌ای", 760_000, None)],
    "مانتو": [("مانتو کتان بلند", 1_450_000, 1_800_000), ("مانتو جلوباز", 1_200_000, None)],
    "کفش": [("کتانی سفید", 1_650_000, None)],
    "کیف و اکسسوری": [("کیف دوشی چرم", 1_100_000, None)],
}


def _png(size, colour, shape="garment"):
    image = Image.new("RGB", size, (245, 243, 240))
    draw = ImageDraw.Draw(image)
    w, h = size
    if shape == "garment":
        draw.polygon([(w * .3, h * .1), (w * .7, h * .1), (w * .9, h * .3), (w * .78, h * .38),
                      (w * .75, h * .9), (w * .25, h * .9), (w * .22, h * .38), (w * .1, h * .3)], fill=colour)
    elif shape == "icon":
        draw.ellipse([w * .15, h * .15, w * .85, h * .85], fill=colour)
    else:  # banner
        draw.rectangle([0, 0, w, h], fill=colour)
        draw.rectangle([w * .05, h * .2, w * .45, h * .8], fill=(255, 255, 255))
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
        for order, (name, tryon_type, colour) in enumerate(CATEGORIES):
            category = Category(name=f"{DEMO_TAG} {name}", tryon_type=tryon_type, show_on_home=True, order=order)
            category.icon.save("icon.png", _png((128, 128), colour, "icon"), save=False)
            category.save()
            categories[name] = (category, colour)

        count = 0
        for cat_name, items in PRODUCTS.items():
            category, colour = categories[cat_name]
            for name, price, before in items:
                product = Product(name=f"{DEMO_TAG} {name}", category=category, price=price, compare_at_price=before,
                                  description="محصول نمونه برای نمایش و توسعه‌ی اپلیکیشن.")
                product.image.save("product.png", _png((600, 800), colour), save=False)
                product.save()
                for size, stock in (("S", 5), ("M", 8), ("L", 3)):
                    ProductVariant.objects.create(product=product, size=size, color="پیش‌فرض", stock=stock)
                count += 1

        first = Product.objects.filter(name__startswith=DEMO_TAG).order_by("pk").first()
        banner = Banner(title=f"{DEMO_TAG} حراج پاییزه", position=Banner.Position.HOME_TOP,
                        link_type=Banner.LinkType.CATEGORY, category=categories["مانتو"][0])
        banner.image.save("banner.png", _png((1200, 500), (31, 56, 100), "banner"), save=False)
        banner.save()
        banner2 = Banner(title=f"{DEMO_TAG} پرو مجازی را امتحان کنید", position=Banner.Position.HOME_MIDDLE,
                         link_type=Banner.LinkType.PRODUCT, product=first)
        banner2.image.save("banner.png", _png((1200, 400), (166, 83, 52), "banner"), save=False)
        banner2.save()

        for order, (title, colour) in enumerate((("تخفیف‌ها", (200, 60, 60)), ("جدیدترین‌ها", (40, 120, 90)),
                                                  ("پرو مجازی", (31, 56, 100)))):
            shortcut = HomeShortcut(title=f"{DEMO_TAG} {title}", order=order, link_type=HomeShortcut.LinkType.CATEGORY,
                                    category=categories["بلوز و شومیز"][0])
            shortcut.icon.save("icon.png", _png((128, 128), colour, "icon"), save=False)
            shortcut.save()

        self.stdout.write(self.style.SUCCESS(
            f"Created {len(categories)} categories, {count} products, 2 banners and 3 home icons."
        ))
