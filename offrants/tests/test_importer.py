from pathlib import Path

from bigday.test_utils import AppTestCase
from offrants.csv_import import import_guests
from offrants.models import Offrant

CSV = Path(__file__).parent / "data" / "guests-test.csv"


class GuestImporterTest(AppTestCase):
    def test_import_creates_guests_with_valid_emails_only(self):
        with self.assertLogs("offrants.csv_import", level="WARNING") as logs:
            created, updated, skipped = import_guests(CSV)
        self.assertEqual((created, updated, skipped), (2, 0, 2))
        self.assertEqual(len(logs.records), 2)
        self.assertEqual(
            sorted(Offrant.objects.values_list("email", flat=True)),
            ["CAT@winterfell.gov", "ned@winterfell.gov"],
        )

    def test_import_is_idempotent_and_updates_names(self):
        import_guests(CSV)
        Offrant.objects.filter(email="ned@winterfell.gov").update(first_name="Eddard")
        created, updated, _ = import_guests(CSV)
        self.assertEqual((created, updated), (0, 2))
        self.assertEqual(Offrant.objects.count(), 2)
        self.assertEqual(Offrant.objects.get(email="ned@winterfell.gov").first_name, "Ned")

    def test_dry_run_changes_nothing(self):
        import_guests(CSV, dry_run=True)
        self.assertEqual(Offrant.objects.count(), 0)

    def test_imported_guest_has_tokens_and_no_usable_password(self):
        import_guests(CSV)
        ned = Offrant.objects.get(email="ned@winterfell.gov")
        self.assertEqual(len(ned.rsvp_id), 32)
        self.assertNotEqual(ned.rsvp_id, ned.invitation_id)
        self.assertFalse(ned.has_usable_password())
