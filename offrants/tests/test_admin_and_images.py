import base64
import tempfile
from pathlib import Path

from django.core import mail
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse

from bigday.test_utils import AppTestCase
from offrants.models import Offrant

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


class AdminTest(AppTestCase):
    def setUp(self):
        self.admin = Offrant.objects.create_superuser("Ada", "Root", "ada@example.org", password="x" * 20)
        self.client.force_login(self.admin)

    def test_changelist_add_and_change_pages_render(self):
        self.assertEqual(self.client.get(reverse("admin:offrants_offrant_changelist")).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:offrants_offrant_add")).status_code, 200)
        self.assertEqual(
            self.client.get(reverse("admin:offrants_offrant_change", args=[self.admin.pk])).status_code, 200
        )
        self.assertEqual(self.client.get(reverse("admin:birthlist_cadeau_add")).status_code, 200)

    def test_admin_created_guest_gets_a_hashed_password(self):
        response = self.client.post(
            reverse("admin:offrants_offrant_add"),
            {
                "first_name": "New",
                "last_name": "Guest",
                "email": "new@example.org",
                "password1": "a-long-unusual-passphrase",
                "password2": "a-long-unusual-passphrase",
                "usable_password": "true",
            },
        )
        self.assertEqual(response.status_code, 302)
        guest = Offrant.objects.get(email="new@example.org")
        self.assertTrue(guest.password.startswith("pbkdf2_"))
        self.assertTrue(guest.check_password("a-long-unusual-passphrase"))


class EmailImageTest(AppTestCase):
    def test_hero_image_is_embedded_from_the_static_dirs(self):
        with tempfile.TemporaryDirectory() as static_dir:
            (Path(static_dir) / "hero.png").write_bytes(PNG)
            Offrant.objects.create_user("Ned", "Stark", "ned@winterfell.gov")
            with override_settings(STATICFILES_DIRS=[static_dir], EMAIL_HERO_IMAGE="hero.png"):
                call_command("send_campaign", "notice", "--send", "--delay", "0")
        message = mail.outbox[0]
        images = [part for part in message.attachments if part.get_content_type() == "image/png"]
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]["Content-ID"], "<hero.png>")
        self.assertIn("cid:hero.png", message.alternatives[0][0])

    def test_missing_image_is_not_fatal(self):
        Offrant.objects.create_user("Ned", "Stark", "ned@winterfell.gov")
        with override_settings(EMAIL_HERO_IMAGE="nope.png"), self.assertLogs("offrants.campaigns", "WARNING"):
            call_command("send_campaign", "notice", "--send", "--delay", "0")
        self.assertEqual(len(mail.outbox), 1)
