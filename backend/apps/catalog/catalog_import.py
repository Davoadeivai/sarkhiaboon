"""
Load the client's filled catalog spreadsheet (see catalog_excel.py) into the store.

Everything is checked first and written in one transaction: if any row has a
problem, nothing is saved and the report lists every problem with its sheet and
row number, in Persian, so the client can fix the file and send it again.
Running the same file again updates the existing records instead of duplicating
them (shops and categories by name, products by code, sizes by code+size+colour,
banners by position+title).
"""
import re
from dataclasses import dataclass, field
from datetime import datetime, time
from pathlib import Path

from django.core.files import File
from django.db import transaction
from django.utils import timezone

from . import catalog_excel as spec
from .models import Banner, Category, Product, ProductImage, ProductVariant, Shop

PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


class ImportFailed(Exception):
    def __init__(self, problems):
        super().__init__("\n".join(problems))
        self.problems = problems


@dataclass
class Report:
    created: dict = field(default_factory=dict)
    updated: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)

    def count(self, kind, created):
        bucket = self.created if created else self.updated
        bucket[kind] = bucket.get(kind, 0) + 1


def _text(value):
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip()


def _number(value):
    """1350000, '1,350,000', '۱٬۳۵۰٬۰۰۰' → 1350000; '' → None."""
    s = _text(value).translate(PERSIAN_DIGITS)
    s = re.sub(r"[,\s٬،]", "", s)
    if not s:
        return None
    if not s.isdigit():
        raise ValueError(s)
    return int(s)


def _jalali(value, end_of_day=False):
    s = _text(value).translate(PERSIAN_DIGITS)
    if not s:
        return None
    m = re.fullmatch(r"(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})", s)
    if not m:
        raise ValueError(s)
    y, mo, d = spec.jalali_to_gregorian(*map(int, m.groups()))
    moment = datetime.combine(datetime(y, mo, d).date(), time.max if end_of_day else time.min)
    return timezone.make_aware(moment)


def _rows(ws, sheet):
    """(row number, {key: value}) for each non-empty data row."""
    keys = [c.key for c in sheet.columns]
    for r in range(spec.FIRST_DATA_ROW, ws.max_row + 1):
        values = {k: ws.cell(r, i + 1).value for i, k in enumerate(keys)}
        if any(_text(v) for v in values.values()):
            yield r, values


def import_catalog(xlsx_path, images_dir=None, dry_run=False):
    from openpyxl import load_workbook

    wb = load_workbook(xlsx_path, data_only=True)
    images = Path(images_dir) if images_dir else None
    problems, report = [], Report()

    def problem(sheet, row, message):
        problems.append(f"برگه‌ی «{sheet.name}»، ردیف {row}: {message}")

    for sheet in spec.SHEETS:
        if sheet.name not in wb.sheetnames:
            problems.append(f"برگه‌ی «{sheet.name}» در فایل نیست؛ از قالب اصلی استفاده کنید.")
            continue
        ws = wb[sheet.name]
        for i, col in enumerate(sheet.columns, start=1):
            header = _text(ws.cell(2, i).value).replace("*", "").strip()
            if header != col.title:
                problems.append(f"برگه‌ی «{sheet.name}»: ستون {i} باید «{col.title}» باشد؛ ترتیب ستون‌ها را تغییر ندهید.")
                break
    if problems:
        raise ImportFailed(problems)

    def image_file(sheet, row, name, required=False):
        name = _text(name)
        if not name:
            if required:
                problem(sheet, row, "نام فایل عکس خالی است.")
            return None
        if images is None:
            if required:
                problem(sheet, row, "پوشه‌ی عکس‌ها داده نشده است (--images).")
            return None
        path = images / name
        if not path.is_file():
            problem(sheet, row, f"فایل عکس «{name}» در پوشه‌ی عکس‌ها پیدا نشد.")
            return None
        return path

    def attach(obj, field_name, path):
        if path is not None:
            with path.open("rb") as fh:
                getattr(obj, field_name).save(path.name, File(fh), save=False)

    with transaction.atomic():
        # ---------- shops
        shops = {}
        for r, row in _rows(wb[spec.SHOPS.name], spec.SHOPS):
            name = _text(row["name"])
            if not name:
                problem(spec.SHOPS, r, "نام فروشگاه خالی است.")
                continue
            if name in shops:
                problem(spec.SHOPS, r, f"فروشگاه «{name}» دو بار آمده است.")
                continue
            shop = Shop.objects.filter(name=name).first()
            created = shop is None
            shop = shop or Shop(name=name)
            shop.city, shop.description = _text(row["city"]), _text(row["description"])
            attach(shop, "logo", image_file(spec.SHOPS, r, row["logo"]))
            attach(shop, "cover", image_file(spec.SHOPS, r, row["cover"]))
            shop.save()
            shops[name] = shop
            report.count("فروشگاه", created)

        # ---------- categories (two passes so a child can come before its parent)
        cats, parents = {}, {}
        for r, row in _rows(wb[spec.CATEGORIES.name], spec.CATEGORIES):
            name = _text(row["name"])
            tryon = spec.TRYON_CHOICES.get(_text(row["tryon"]))
            if not name:
                problem(spec.CATEGORIES, r, "نام دسته خالی است.")
                continue
            if name in cats:
                problem(spec.CATEGORIES, r, f"دسته‌ی «{name}» دو بار آمده است.")
                continue
            if tryon is None:
                problem(spec.CATEGORIES, r, "نوع پرو مجازی را از فهرست انتخاب کنید.")
                continue
            try:
                order = _number(row["order"]) or 0
            except ValueError:
                problem(spec.CATEGORIES, r, "ترتیب باید عدد باشد.")
                continue
            cat = Category.objects.filter(name=name).first()
            created = cat is None
            cat = cat or Category(name=name)
            cat.tryon_type, cat.order, cat.is_active = tryon, order, True
            cat.show_on_home = spec.YES_NO.get(_text(row["home"]), False)
            attach(cat, "image", image_file(spec.CATEGORIES, r, row["image"]))
            cat.save()
            cats[name] = cat
            parents[name] = (r, _text(row["parent"]))
            report.count("دسته", created)
        for name, (r, parent_name) in parents.items():
            if not parent_name:
                if cats[name].parent_id:
                    cats[name].parent = None
                    cats[name].save(update_fields=["parent"])
                continue
            parent = cats.get(parent_name) or Category.objects.filter(name=parent_name).first()
            if parent is None:
                problem(spec.CATEGORIES, r, f"دسته‌ی والد «{parent_name}» پیدا نشد.")
            elif parent.pk == cats[name].pk:
                problem(spec.CATEGORIES, r, "دسته نمی‌تواند والد خودش باشد.")
            else:
                cats[name].parent = parent
                cats[name].save(update_fields=["parent"])

        def find_category(name):
            return cats.get(name) or Category.objects.filter(name=name).first()

        # ---------- products
        products = {}
        for r, row in _rows(wb[spec.PRODUCTS.name], spec.PRODUCTS):
            code, name = _text(row["code"]), _text(row["name"])
            missing = [c.title for c in spec.PRODUCTS.columns if c.required and not _text(row[c.key])]
            if missing:
                problem(spec.PRODUCTS, r, "خالی است: " + "، ".join(missing))
                continue
            if code in products:
                problem(spec.PRODUCTS, r, f"کد «{code}» تکراری است.")
                continue
            shop = shops.get(_text(row["shop"])) or Shop.objects.filter(name=_text(row["shop"])).first()
            category = find_category(_text(row["category"]))
            if shop is None:
                problem(spec.PRODUCTS, r, f"فروشگاه «{_text(row['shop'])}» در برگه‌ی فروشگاه‌ها نیست.")
            if category is None:
                problem(spec.PRODUCTS, r, f"دسته‌ی «{_text(row['category'])}» در برگه‌ی دسته‌ها نیست.")
            try:
                price, compare_at = _number(row["price"]), _number(row["compare_at"])
            except ValueError:
                problem(spec.PRODUCTS, r, "قیمت‌ها باید فقط عدد باشند.")
                continue
            if compare_at is not None and compare_at <= price:
                problem(spec.PRODUCTS, r, "قیمت قبل از تخفیف باید بیشتر از قیمت باشد.")
            product = Product.objects.filter(code=code).first()
            main_image = image_file(spec.PRODUCTS, r, row["image"], required=product is None)
            garment = image_file(spec.PRODUCTS, r, row["garment"])
            gallery = [image_file(spec.PRODUCTS, r, n) for n in re.split(r"[,،]", _text(row["gallery"])) if n.strip()]
            if shop is None or category is None or (product is None and main_image is None):
                continue
            created = product is None
            product = product or Product(code=code)
            product.name, product.shop, product.category = name, shop, category
            product.price, product.compare_at_price = price, compare_at
            product.description = _text(row["description"])
            product.tryon_enabled = spec.YES_NO.get(_text(row["tryon"]), True)
            product.is_active = True
            attach(product, "image", main_image)
            attach(product, "garment_image", garment)
            product.save()
            if any(gallery):
                product.images.all().delete()
                for k, path in enumerate(p for p in gallery if p):
                    with path.open("rb") as fh:
                        ProductImage.objects.create(product=product, image=File(fh, name=path.name), order=k)
            if product.supports_tryon and not product.garment_image:
                report.warnings.append(f"محصول {code}: عکس تمیز برای پرو ندارد؛ پرو با عکس اصلی انجام می‌شود و کیفیتش پایین‌تر است.")
            products[code] = product
            report.count("محصول", created)

        # ---------- sizes and stock
        seen = set()
        for r, row in _rows(wb[spec.VARIANTS.name], spec.VARIANTS):
            code = _text(row["code"])
            product = products.get(code) or Product.objects.filter(code=code).first()
            if product is None:
                problem(spec.VARIANTS, r, f"کد محصول «{code}» در برگه‌ی محصولات نیست.")
                continue
            size, color = _text(row["size"]), _text(row["color"])
            if (code, size, color) in seen:
                problem(spec.VARIANTS, r, "این سایز و رنگ برای این محصول دو بار آمده است.")
                continue
            seen.add((code, size, color))
            try:
                stock, price = _number(row["stock"]), _number(row["price"])
            except ValueError:
                problem(spec.VARIANTS, r, "موجودی و قیمت باید فقط عدد باشند.")
                continue
            if stock is None:
                problem(spec.VARIANTS, r, "موجودی خالی است.")
                continue
            hex_ = _text(row["color_hex"])
            if hex_ and not re.fullmatch(r"#[0-9A-Fa-f]{6}", hex_):
                problem(spec.VARIANTS, r, "کد رنگ باید مثل #1F3864 باشد.")
                continue
            variant, created = ProductVariant.objects.update_or_create(
                product=product, size=size, color=color,
                defaults={"stock": stock, "price_override": price, "color_hex": hex_, "is_active": True},
            )
            report.count("سایز/رنگ", created)

        # ---------- banners
        for r, row in _rows(wb[spec.BANNERS.name], spec.BANNERS):
            position = spec.BANNER_POSITIONS.get(_text(row["position"]))
            title = _text(row["title"])
            if position is None or not title:
                problem(spec.BANNERS, r, "جایگاه و عنوان الزامی‌اند.")
                continue
            page = None
            if position == "category_top":
                page = find_category(_text(row["page"]))
                if page is None:
                    problem(spec.BANNERS, r, "دسته‌ی محل نمایش را از فهرست انتخاب کنید.")
                    continue
            try:
                starts, ends = _jalali(row["starts"]), _jalali(row["ends"], end_of_day=True)
                order = _number(row["order"]) or 0
            except ValueError:
                problem(spec.BANNERS, r, "تاریخ‌ها باید شمسی و مثل 1405/09/01 باشند و ترتیب عدد.")
                continue
            if starts and ends and ends < starts:
                problem(spec.BANNERS, r, "تاریخ پایان قبل از تاریخ شروع است.")
                continue
            link_type = spec.LINK_TYPES.get(_text(row["link_type"]) or "بدون لینک", "none")
            target = _text(row["link"])
            banner = Banner.objects.filter(position=position, title=title, placement_category=page).first()
            created = banner is None
            banner = banner or Banner(position=position, title=title, placement_category=page)
            banner.link_type, banner.product, banner.category, banner.url = link_type, None, None, ""
            if link_type == "category":
                banner.category = find_category(target)
                if banner.category is None:
                    problem(spec.BANNERS, r, f"دسته‌ی مقصد «{target}» پیدا نشد.")
            elif link_type == "product":
                banner.product = products.get(target) or Product.objects.filter(code=target).first()
                if banner.product is None:
                    problem(spec.BANNERS, r, f"محصول با کد «{target}» پیدا نشد.")
            elif link_type == "url":
                if not target.startswith(("http://", "https://")):
                    problem(spec.BANNERS, r, "نشانی اینترنتی باید با https:// شروع شود.")
                banner.url = target
            path = image_file(spec.BANNERS, r, row["image"], required=created)
            if created and path is None:
                continue
            attach(banner, "image", path)
            banner.starts_at, banner.ends_at, banner.order, banner.is_active = starts, ends, order, True
            banner.save()
            report.count("بنر", created)

        if problems:
            transaction.set_rollback(True)
            raise ImportFailed(problems)
        if dry_run:
            transaction.set_rollback(True)
    return report
