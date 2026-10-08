from django.core.management import BaseCommand

from offrants.models import Offrant


class Command(BaseCommand):
    help = "Delete every non-staff guest."

    def handle(self, *args, **kwargs):
        guests = Offrant.objects.filter(is_staff=False, is_superuser=False)
        count = guests.count()
        if input(f"Really delete all {count} guests? (y/n) ") == "y":
            guests.delete()
            self.stdout.write("Guests deleted")
        else:
            self.stdout.write("Cancelled")
