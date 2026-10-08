from django.core.management import BaseCommand

from offrants import csv_import


class Command(BaseCommand):
    help = "Write the guest list as CSV on stdout."

    def handle(self, *args, **options):
        self.stdout.write(csv_import.export_guests().getvalue(), ending="")
