from django.conf import settings


def site(request):
    """Expose the (non-secret) site identity settings to every template."""
    return {
        "site_title": settings.SITE_TITLE,
        "couple_names": settings.COUPLE_NAMES,
        "baby_name": settings.BABY_NAME,
        "support_email": settings.BIRTHLIST_REPLY_EMAIL,
        "header_image": settings.HEADER_IMAGE,
        "gift_pot_url": settings.GIFT_POT_URL,
        "postal_address": settings.POSTAL_ADDRESS,
        "registration_enabled": bool(settings.REGISTRATION_CODE),
    }
