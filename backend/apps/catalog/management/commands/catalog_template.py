from django.core.management.base import BaseCommand

from apps.catalog.catalog_excel import build_template


class Command(BaseCommand):
    help = "Write the blank catalog spreadsheet for the client (shops, categories, products, sizes, banners)."

    def add_arguments(self, parser):
        parser.add_argument("output", help="Path of the .xlsx file to write")

    def handle(self, *args, output, **options):
        build_template(output)
        self.stdout.write(self.style.SUCCESS(f"Template written to {output}"))
