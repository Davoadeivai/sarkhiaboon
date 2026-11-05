from django.core.management.base import BaseCommand, CommandError

from apps.catalog.catalog_import import ImportFailed, import_catalog


class Command(BaseCommand):
    help = (
        "Load the client's filled catalog spreadsheet (shops, categories, products, sizes, banners). "
        "Nothing is saved if any row has a problem; run again after fixing."
    )

    def add_arguments(self, parser):
        parser.add_argument("xlsx", help="The filled template (.xlsx)")
        parser.add_argument("--images", help="Folder that holds every image named in the spreadsheet")
        parser.add_argument("--dry-run", action="store_true", help="Only check the file; save nothing")

    def handle(self, *args, xlsx, images=None, dry_run=False, **options):
        try:
            report = import_catalog(xlsx, images, dry_run=dry_run)
        except ImportFailed as exc:
            for line in exc.problems:
                self.stderr.write(f"✗ {line}")
            raise CommandError(f"{len(exc.problems)} مشکل پیدا شد؛ هیچ تغییری ذخیره نشد.")
        for line in report.warnings:
            self.stdout.write(self.style.WARNING(f"! {line}"))
        made = "، ".join(f"{n} {k}" for k, n in report.created.items()) or "هیچ"
        changed = "، ".join(f"{n} {k}" for k, n in report.updated.items()) or "هیچ"
        prefix = "بررسی موفق (ذخیره نشد — dry-run). " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(f"{prefix}ساخته شد: {made}. به‌روز شد: {changed}."))
