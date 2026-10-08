import csv
import io
from datetime import timedelta
from io import StringIO
from pathlib import Path
from unittest import mock

from django.core.management import call_command
from django.utils import timezone

from bigday.test_utils import AppTestCase
from offrants.models import Offrant

CSV = Path(__file__).parent / "data" / "guests-test.csv"


class GuestCommandsTest(AppTestCase):
    def test_import_then_export_round_trip(self):
        out = StringIO()
        with self.assertLogs("offrants.csv_import", level="WARNING"):
            call_command("import_guests", str(CSV), stdout=out)
        self.assertIn("2 created", out.getvalue())
        exported = StringIO()
        call_command("export_guests", stdout=exported)
        rows = list(csv.reader(io.StringIO(exported.getvalue())))
        self.assertEqual(rows[0], ["first_name", "last_name", "email"])
        self.assertEqual({r[2] for r in rows[1:]}, {"CAT@winterfell.gov", "ned@winterfell.gov"})

    def test_import_dry_run(self):
        out = StringIO()
        with self.assertLogs("offrants.csv_import", level="WARNING"):
            call_command("import_guests", str(CSV), "--dry-run", stdout=out)
        self.assertIn("[dry-run]", out.getvalue())
        self.assertFalse(Offrant.objects.exists())

    def test_purge_keeps_recent_guests_and_staff(self):
        old = timezone.now() - timedelta(days=200)
        Offrant.objects.create_user("Old", "Guest", "old@example.org")
        Offrant.objects.create_user("New", "Guest", "new@example.org")
        Offrant.objects.create_superuser("Old", "Admin", "admin@example.org", password="x" * 20)
        Offrant.objects.filter(email__in=["old@example.org", "admin@example.org"]).update(created=old)
        call_command("purge_guests", "--yes", stdout=StringIO())
        self.assertEqual(
            sorted(Offrant.objects.values_list("email", flat=True)), ["admin@example.org", "new@example.org"]
        )

    def test_wipe_guest_list_asks_for_confirmation_and_spares_staff(self):
        Offrant.objects.create_user("A", "B", "a@example.org")
        Offrant.objects.create_superuser("Admin", "Root", "admin@example.org", password="x" * 20)
        with mock.patch("builtins.input", return_value="n"):
            call_command("wipe_guest_list", stdout=StringIO())
        self.assertEqual(Offrant.objects.count(), 2)
        with mock.patch("builtins.input", return_value="y"):
            call_command("wipe_guest_list", stdout=StringIO())
        self.assertEqual(list(Offrant.objects.values_list("email", flat=True)), ["admin@example.org"])


class ModelTest(AppTestCase):
    def test_superuser_flags_and_names(self):
        admin = Offrant.objects.create_superuser("Ada", "Lovelace", "ada@example.org", password="x" * 20)
        self.assertTrue(admin.is_staff and admin.is_superuser and admin.check_password("x" * 20))
        self.assertEqual(
            (admin.name, admin.get_full_name(), admin.get_short_name(), str(admin)),
            ("Ada Lovelace",) * 2 + ("Ada", "Ada Lovelace"),
        )

    def test_email_is_required(self):
        with self.assertRaises(ValueError):
            Offrant.objects.create_user("No", "Mail", "")
