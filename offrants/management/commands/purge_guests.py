from datetime import timedelta

from django.core.management import BaseCommand
from django.utils import timezone

from offrants.models import Offrant


class Command(BaseCommand):
    help = "Delete guest accounts (never staff) created more than N days ago, to honour the retention promise."

    def add_arguments(self, parser):
        parser.add_argument("--older-than-days", type=int, default=180)
        parser.add_argument("--yes", action="store_true", help="Do not ask for confirmation")

    def handle(self, *args, older_than_days, yes, **options):
        queryset = Offrant.objects.filter(
            created__lt=timezone.now() - timedelta(days=older_than_days), is_staff=False, is_superuser=False
        )
        count = queryset.count()
        if not yes and input(f"Delete {count} guests created more than {older_than_days} days ago? (y/n) ") != "y":
            self.stdout.write("Cancelled")
            return
        queryset.delete()
        self.stdout.write(f"{count} guests deleted")
