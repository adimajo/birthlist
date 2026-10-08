from io import StringIO
from unittest import mock

from django.core import mail
from django.core.management import CommandError, call_command
from django.urls import reverse

from bigday.test_utils import AppTestCase
from offrants.campaigns import ANNOUNCEMENT, NOTICE
from offrants.models import Offrant


class MagicLinkTest(AppTestCase):
    def setUp(self):
        self.guest = Offrant.objects.create_user("Ned", "Stark", "ned@winterfell.gov")

    def test_notice_link_logs_in_and_records_opening(self):
        response = self.client.get(reverse("invitation", args=[self.guest.invitation_id]))
        self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)
        self.assertEqual(self.client.session["_auth_user_id"], self.guest.pk)
        self.guest.refresh_from_db()
        self.assertIsNotNone(self.guest.invitation_opened)
        self.assertIsNone(self.guest.rsvp_opened)

    def test_announcement_link_logs_in(self):
        self.client.get(reverse("rsvp", args=[self.guest.rsvp_id]))
        self.guest.refresh_from_db()
        self.assertIsNotNone(self.guest.rsvp_opened)

    def test_first_opening_time_is_kept(self):
        self.client.get(reverse("rsvp", args=[self.guest.rsvp_id]))
        self.guest.refresh_from_db()
        first = self.guest.rsvp_opened
        self.client.get(reverse("rsvp", args=[self.guest.rsvp_id]))
        self.guest.refresh_from_db()
        self.assertEqual(self.guest.rsvp_opened, first)

    def test_unknown_token_is_404_and_does_not_log_in(self):
        response = self.client.get(reverse("invitation", args=["0" * 32]))
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_tokens_are_not_interchangeable_between_campaigns(self):
        response = self.client.get(reverse("rsvp", args=[self.guest.invitation_id]))
        self.assertEqual(response.status_code, 404)


class SendCampaignTest(AppTestCase):
    def setUp(self):
        self.a = Offrant.objects.create_user("Ned", "Stark", "ned@winterfell.gov")
        self.b = Offrant.objects.create_user("Cat", "Stark", "cat@winterfell.gov")

    def run_command(self, *args):
        out = StringIO()
        call_command("send_campaign", *args, "--delay", "0", stdout=out)
        return out.getvalue()

    def test_dry_run_sends_and_marks_nothing(self):
        self.run_command("announcement")
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(Offrant.objects.exclude(rsvp_sent=None).count(), 0)

    def test_mark_sent_requires_send(self):
        with self.assertRaises(CommandError):
            self.run_command("announcement", "--mark-sent")

    def test_send_builds_personal_message(self):
        self.run_command("announcement", "--send", "--mark-sent")
        self.assertEqual(len(mail.outbox), 2)
        message = next(m for m in mail.outbox if m.to == ["ned@winterfell.gov"])
        self.assertEqual(message.cc, ["cc@example.org"])
        self.assertEqual(message.reply_to, ["contact@example.org"])
        self.assertEqual(message.from_email, "Parents <parents@example.org>")
        html = message.alternatives[0][0]
        self.assertIn(f"https://birthlist.example.org/rsvp/{self.a.rsvp_id}/", html)
        self.assertEqual(Offrant.objects.exclude(rsvp_sent=None).count(), 2)

    def test_already_sent_guests_are_skipped(self):
        self.run_command("notice", "--send", "--mark-sent")
        mail.outbox.clear()
        self.run_command("notice", "--send", "--mark-sent")
        self.assertEqual(len(mail.outbox), 0)

    def test_send_without_mark_sent_does_not_mark(self):
        self.run_command("notice", "--send")
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(Offrant.objects.exclude(invitation_sent=None).count(), 0)

    def test_failure_for_one_guest_does_not_stop_others_nor_mark_it(self):
        real_send = mail.EmailMultiAlternatives.send

        def flaky(message, *args, **kwargs):
            if message.to == ["ned@winterfell.gov"]:
                raise OSError("smtp down")
            return real_send(message, *args, **kwargs)

        with mock.patch.object(mail.EmailMultiAlternatives, "send", flaky), self.assertLogs("offrants.campaigns"):
            with self.assertRaises(CommandError):
                self.run_command("announcement", "--send", "--mark-sent")
        self.a.refresh_from_db()
        self.b.refresh_from_db()
        self.assertIsNone(self.a.rsvp_sent)
        self.assertIsNotNone(self.b.rsvp_sent)

    def test_reset_clears_sent_flags(self):
        self.run_command("announcement", "--send", "--mark-sent")
        self.assertEqual(ANNOUNCEMENT.reset_sent(), 2)
        self.assertEqual(Offrant.objects.exclude(rsvp_sent=None).count(), 0)
        self.assertEqual(NOTICE.reset_sent(), 0)


class StaffToolsTest(AppTestCase):
    def setUp(self):
        self.guest = Offrant.objects.create_user("Ned", "Stark", "ned@winterfell.gov", password="s3cret-pass-word")
        self.staff = Offrant.objects.create_superuser("Admin", "Root", "admin@example.org", password="s3cret-pass-word")

    def test_dashboard_permissions(self):
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 302)
        self.client.force_login(self.guest)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)

    def test_previews_staff_only(self):
        for name in ("rsvp-email", "invitation-email"):
            self.client.force_login(self.guest)
            self.assertEqual(self.client.get(reverse(name)).status_code, 302)
            self.client.force_login(self.staff)
            self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_test_send_is_post_only_staff_only_and_goes_to_requester_without_cc(self):
        url = reverse("rsvp-email-test")
        self.client.force_login(self.guest)
        self.client.post(url)
        self.assertEqual(len(mail.outbox), 0)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url).status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["admin@example.org"])
        self.assertEqual(mail.outbox[0].cc, [])

    def test_no_public_guest_list_or_csv_export(self):
        for path in ("/offrants/", "/offrants/export"):
            self.assertEqual(self.client.get(path).status_code, 404)
            self.client.force_login(self.guest)
            self.assertEqual(self.client.get(path).status_code, 404)
