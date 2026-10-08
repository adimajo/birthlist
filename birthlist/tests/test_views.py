from decimal import Decimal
from unittest import mock

from django.core import mail
from django.urls import reverse

from bigday.test_utils import AppTestCase
from birthlist.models import Cadeau
from offrants.models import Offrant


class GiftViewsTest(AppTestCase):
    def setUp(self):
        self.guest = Offrant.objects.create_user("Ned", "Stark", "ned@winterfell.gov", password="s3cret-pass-word")
        self.other = Offrant.objects.create_user("Cat", "Stark", "cat@winterfell.gov")
        self.pram = Cadeau.objects.create(name="Poussette", price=Decimal("300.00"))
        self.cot = Cadeau.objects.create(name="Lit / bébé?", price=Decimal("120.50"))

    def test_home_requires_login(self):
        response = self.client.get(reverse("home"))
        self.assertRedirects(response, f"{reverse('login')}?next=/", fetch_redirect_response=False)

    def test_home_lists_gifts_without_n_plus_one(self):
        self.client.force_login(self.guest)
        with self.assertNumQueries(5):  # session, user, gifts, interested, bought
            response = self.client.get(reverse("home"))
        self.assertContains(response, "Poussette")
        self.assertContains(response, "Lit / bébé?")

    def test_sorting_allow_list(self):
        self.client.force_login(self.guest)
        response = self.client.get(reverse("home"), {"order_by": "price", "direction": "desc"})
        self.assertEqual([g.name for g in response.context["gifts"]], ["Poussette", "Lit / bébé?"])
        response = self.client.get(reverse("home"), {"order_by": "price"})
        self.assertEqual([g.name for g in response.context["gifts"]], ["Lit / bébé?", "Poussette"])
        response = self.client.get(reverse("home"), {"order_by": "password; DROP TABLE"})
        self.assertEqual(response.status_code, 200)

    def test_actions_are_post_only(self):
        self.client.force_login(self.guest)
        for name in ("interet", "not_interet", "bought", "not_bought"):
            self.assertEqual(self.client.get(reverse(name, args=[self.pram.pk])).status_code, 405)
        self.assertEqual(self.pram.interested_families.count(), 0)

    def test_actions_require_login(self):
        response = self.client.post(reverse("interet", args=[self.pram.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.pram.interested_families.count(), 0)

    def test_interest_and_purchase_toggle_idempotently(self):
        self.client.force_login(self.guest)
        for _ in range(2):
            response = self.client.post(reverse("interet", args=[self.pram.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(list(self.pram.interested_families.all()), [self.guest])
        self.client.post(reverse("not_interet", args=[self.pram.pk]))
        self.assertEqual(self.pram.interested_families.count(), 0)
        self.client.post(reverse("bought", args=[self.pram.pk]))
        self.assertEqual(list(self.pram.bought_by.all()), [self.guest])
        self.client.post(reverse("not_bought", args=[self.pram.pk]))
        self.assertEqual(self.pram.bought_by.count(), 0)

    def test_actions_only_touch_the_current_user(self):
        self.pram.interested_families.add(self.other)
        self.client.force_login(self.guest)
        self.client.post(reverse("not_interet", args=[self.pram.pk]))
        self.assertEqual(list(self.pram.interested_families.all()), [self.other])

    def test_unknown_gift_is_404(self):
        self.client.force_login(self.guest)
        self.assertEqual(self.client.post(reverse("interet", args=[9999])).status_code, 404)

    def test_gifts_with_awkward_names_work(self):
        self.client.force_login(self.guest)
        self.assertEqual(self.client.post(reverse("interet", args=[self.cot.pk])).status_code, 302)
        Cadeau.objects.create(name="Poussette", price=1)  # duplicate names no longer break anything
        self.assertEqual(self.client.post(reverse("interet", args=[self.pram.pk])).status_code, 302)

    def test_healthz_is_public(self):
        response = self.client.get(reverse("healthz"))
        self.assertEqual((response.status_code, response.content), (200, b"ok"))


class RegistrationTest(AppTestCase):
    data = {
        "first_name": "Arya",
        "last_name": "Stark",
        "email": "arya@winterfell.gov",
        "password1": "a-long-unusual-passphrase",
        "password2": "a-long-unusual-passphrase",
        "registration_code": "sesame",
    }

    def test_register_with_code_logs_in(self):
        response = self.client.post(reverse("register"), self.data)
        self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)
        self.assertTrue(Offrant.objects.filter(email="arya@winterfell.gov").exists())
        self.assertIn("_auth_user_id", self.client.session)

    def test_wrong_code_is_rejected(self):
        response = self.client.post(reverse("register"), {**self.data, "registration_code": "nope"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Offrant.objects.exists())

    def test_cannot_register_over_an_existing_email(self):
        Offrant.objects.create_user("Arya", "Imported", "ARYA@winterfell.gov")
        response = self.client.post(reverse("register"), self.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Offrant.objects.count(), 1)

    def test_registration_disabled_without_code(self):
        with self.settings(REGISTRATION_CODE=""):
            self.assertEqual(self.client.get(reverse("register")).status_code, 404)
            self.assertEqual(self.client.post(reverse("register"), self.data).status_code, 404)
            self.assertFalse(Offrant.objects.exists())


class PasswordResetTest(AppTestCase):
    def test_old_unauthenticated_reset_by_name_is_gone(self):
        victim = Offrant.objects.create_user("Ned", "Stark", "ned@winterfell.gov", password="original-password-1")
        response = self.client.post(
            "/password",
            {
                "first_name": "Ned",
                "last_name": "Stark",
                "email": "ned@winterfell.gov",
                "new_password1": "hacked-password-99",
                "new_password2": "hacked-password-99",
            },
        )
        self.assertEqual(response.status_code, 404)
        victim.refresh_from_db()
        self.assertTrue(victim.check_password("original-password-1"))

    def test_reset_by_email_link_works_even_for_imported_guests(self):
        guest = Offrant.objects.create_user("Ned", "Stark", "ned@winterfell.gov")
        self.assertFalse(guest.has_usable_password())
        self.client.post(reverse("password_reset"), {"email": "ned@winterfell.gov"})
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("https://birthlist.example.org/password/reset/", mail.outbox[0].body)
        link = next(line for line in mail.outbox[0].body.splitlines() if line.startswith("https://"))
        response = self.client.get(link.replace("https://birthlist.example.org", ""), follow=True)
        post_url = response.redirect_chain[-1][0]
        passwords = {"new_password1": "brand-new-passphrase-7", "new_password2": "brand-new-passphrase-7"}
        response = self.client.post(post_url, passwords)
        self.assertEqual(response.status_code, 302)
        guest.refresh_from_db()
        self.assertTrue(guest.check_password("brand-new-passphrase-7"))

    def test_unknown_email_does_not_leak(self):
        response = self.client.post(reverse("password_reset"), {"email": "nobody@example.org"})
        self.assertRedirects(response, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 0)


class HeaderImageTest(AppTestCase):
    def setUp(self):
        self.guest = Offrant.objects.create_user("Ned", "Stark", "ned@winterfell.gov")
        self.client.force_login(self.guest)

    def test_header_image_is_optional(self):
        with self.settings(HEADER_IMAGE=""):
            response = self.client.get(reverse("home"))
        self.assertNotContains(response, 'id="main-header"')

    def test_missing_header_image_does_not_break_the_page(self):
        with (
            self.settings(HEADER_IMAGE="bigday/images/missing.jpg"),
            mock.patch(
                "bigday.context_processors.staticfiles_storage", **{"url.side_effect": ValueError("no manifest")}
            ),
            self.assertLogs("bigday.context_processors", "WARNING"),
        ):
            response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="main-header"')

    def test_configured_header_image_is_rendered(self):
        with self.settings(HEADER_IMAGE="favicon.ico", HEADER_IMAGE_FIT="contain"):
            response = self.client.get(reverse("home"))
        self.assertContains(response, 'id="main-header"')
        self.assertContains(response, "background-size: contain")
