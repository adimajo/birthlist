from django.core.management import BaseCommand

from offrants import csv_import


class Command(BaseCommand):
    help = "Import guests from a CSV file (first name, last name, email)."

    def add_arguments(self, parser):
        parser.add_argument("filename", type=str)
        parser.add_argument("--dry-run", action="store_true", help="Only report what would change")

    def handle(self, filename, *args, dry_run=False, **options):
        created, updated, skipped = csv_import.import_guests(filename, dry_run=dry_run)
        prefix = "[dry-run] " if dry_run else ""
        self.stdout.write(f"{prefix}{created} created, {updated} already present, {skipped} skipped")
