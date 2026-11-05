"""The client's spreadsheet → store: template, full import, re-import, and error reporting."""
import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import CommandError, call_command
from django.utils import timezone
from openpyxl import load_workbook
from PIL import Image

from apps.core.testing import APITestBase

from .catalog_excel import FIRST_DATA_ROW, build_template, jalali_to_gregorian
from .models import Banner, Category, Product, ProductVariant, Shop


class CatalogImportTests(APITestBase):
    def setUp(self):
        super().setUp()
        self.dir = Path(tempfile.mkdtemp())
        self.images = self.dir / "images"
        self.images.mkdir()
        for name in ("lale-logo.png", "M-101.jpg", "M-101-clean.jpg", "M-101-2.jpg", "M-102.jpg", "office.jpg", "banner.jpg"):
            Image.new("RGB", (400, 500), (120, 30, 40)).save(self.images / name)
        self.xlsx = self.dir / "catalog.xlsx"
        build_template(self.xlsx)

    def fill(self, sheet, rows, start=FIRST_DATA_ROW):
        wb = load_workbook(self.xlsx)
        ws = wb[sheet]
        for i, row in enumerate(rows):
            for j, value in enumerate(row):
                ws.cell(start + i, j + 1, value if value != "" else None)
        wb.save(self.xlsx)

    def fill_valid(self):
        self.fill("فروشگاه‌ها", [["بوتیک لاله", "تهران", "مانتو روزمره", "lale-logo.png", ""]])
        # Categories are pre-filled in the template (مانتو + 4 subcategories, …); add a tile image to one.
        self.fill("دسته‌ها", [["مانتو اداری", "مانتو", "لباس یک‌تکه", "خیر", "office.jpg", 2]], start=FIRST_DATA_ROW + 2)
        self.fill("محصولات", [
            ["M-101", "مانتو اداری کرپ", "بوتیک لاله", "مانتو اداری", 1350000, "1,550,000", "کرپ نرم", "M-101.jpg", "M-101-clean.jpg", "M-101-2.jpg", "بله"],
            ["M-102", "مانتو اداری بلند", "بوتیک لاله", "مانتو اداری", "۱۴۸۰۰۰۰", "", "", "M-102.jpg", "", "", ""],
        ])
        self.fill("سایز و موجودی", [["M-101", "M", "مشکی", "#1C1A2B", 8, ""], ["M-101", "L", "مشکی", "", 3, 1400000], ["M-102", "", "", "", 5, ""]])
        self.fill("بنرها", [
            ["بالای صفحه‌ی اصلی", "", "حراج پاییزه", "banner.jpg", "دسته", "مانتو", "1405/09/01", "1405/09/30", 1],
            ["بالای صفحه‌ی دسته", "مانتو اداری", "اداری نو", "banner.jpg", "محصول", "M-101", "", "", 1],
        ])

    def run_import(self, *extra):
        out = StringIO()
        call_command("import_catalog", str(self.xlsx), "--images", str(self.images), *extra, stdout=out, stderr=StringIO())
        return out.getvalue()

    def test_jalali_dates(self):
        self.assertEqual(jalali_to_gregorian(1405, 8, 14), (2026, 11, 5))
        self.assertEqual(jalali_to_gregorian(1403, 12, 30), (2025, 3, 20))  # leap year end

    def test_full_import(self):
        self.fill_valid()
        out = self.run_import()
        self.assertIn("ساخته شد", out)
        shop = Shop.objects.get(name="بوتیک لاله")
        self.assertTrue(shop.logo)
        office = Category.objects.get(name="مانتو اداری")
        self.assertEqual(office.parent.name, "مانتو")
        self.assertEqual(office.tryon_type, "dresses")
        self.assertTrue(office.image)
        self.assertEqual(Category.objects.get(name="کیف و اکسسوری").tryon_type, "none")
        p = Product.objects.get(code="M-101")
        self.assertEqual((p.shop, p.category, p.price, p.compare_at_price), (shop, office, 1350000, 1550000))
        self.assertTrue(p.garment_image)
        self.assertEqual(p.images.count(), 1)
        self.assertEqual(Product.objects.get(code="M-102").price, 1480000)  # Persian digits
        self.assertEqual(ProductVariant.objects.get(product=p, size="L").price, 1400000)
        top = Banner.objects.get(title="حراج پاییزه")
        self.assertEqual((top.position, top.category.name), ("home_top", "مانتو"))
        # 1405/09/01 at midnight in the store's time zone (Tehran)
        self.assertEqual(timezone.localtime(top.starts_at).date().isoformat(), "2026-11-22")
        page = Banner.objects.get(title="اداری نو")
        self.assertEqual((page.placement_category, page.product), (office, p))
        self.assertIn("M-102", out)  # warned: no clean try-on photo

    def test_reimport_updates_instead_of_duplicating(self):
        self.fill_valid()
        self.run_import()
        self.fill("محصولات", [["M-101", "مانتو اداری کرپ", "بوتیک لاله", "مانتو اداری", 1290000, "", "", "M-101.jpg", "", "", "بله"]])
        out = self.run_import()
        self.assertIn("به‌روز شد", out)
        self.assertEqual(Product.objects.filter(code="M-101").count(), 1)
        self.assertEqual(Product.objects.get(code="M-101").price, 1290000)
        self.assertEqual(Shop.objects.count(), 1)
        self.assertEqual(Banner.objects.count(), 2)

    def test_problems_are_reported_and_nothing_is_saved(self):
        self.fill_valid()
        self.fill("محصولات", [["M-103", "مانتو بی‌فروشگاه", "مزون ناشناس", "مانتو اداری", 900000, 800000, "", "missing.jpg", "", "", ""]],
                  start=FIRST_DATA_ROW + 2)
        self.fill("سایز و موجودی", [["X-9", "M", "", "", 2, ""]], start=FIRST_DATA_ROW + 3)
        err = StringIO()
        with self.assertRaises(CommandError):
            call_command("import_catalog", str(self.xlsx), "--images", str(self.images), stdout=StringIO(), stderr=err)
        text = err.getvalue()
        self.assertIn("مزون ناشناس", text)
        self.assertIn("missing.jpg", text)
        self.assertIn("قیمت قبل از تخفیف", text)
        self.assertIn("X-9", text)
        self.assertIn(f"ردیف {FIRST_DATA_ROW + 2}", text)
        # Atomic: the valid rows were not saved either.
        self.assertFalse(Shop.objects.exists())
        self.assertFalse(Product.objects.exists())

    def test_dry_run_saves_nothing(self):
        self.fill_valid()
        out = self.run_import("--dry-run")
        self.assertIn("dry-run", out)
        self.assertFalse(Product.objects.exists())

    def test_changed_columns_are_refused(self):
        wb = load_workbook(self.xlsx)
        wb["محصولات"].cell(2, 1, "کد")
        wb.save(self.xlsx)
        with self.assertRaises(CommandError):
            call_command("import_catalog", str(self.xlsx), stdout=StringIO(), stderr=StringIO())
