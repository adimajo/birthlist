from django.test import TestCase, override_settings

PLAIN_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(
    STORAGES=PLAIN_STORAGES,
    REGISTRATION_CODE="Sesame",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    BIRTHLIST_CC_LIST=["cc@example.org"],
    BIRTHLIST_REPLY_EMAIL="contact@example.org",
    DEFAULT_FROM_EMAIL="Parents <parents@example.org>",
    SITE_URL="https://birthlist.example.org",
    EMAIL_HERO_IMAGE="",
    HEADER_IMAGE="",
    GIFT_POT_URL="",
    POSTAL_ADDRESS=[],
)
class AppTestCase(TestCase):
    """Base class: no static manifest needed, in-memory mail, known registration code."""
