"""E-mail campaigns sent to guests.

Two campaigns exist, each with its own per-guest secret token and sent/opened timestamps:

* ``announcement`` ("annonce", the former *save the date*): ``rsvp_id`` / ``rsvp_sent`` / ``rsvp_opened``
* ``notice`` ("faire-part"): ``invitation_id`` / ``invitation_sent`` / ``invitation_opened``

The wording lives in the ``offrants/email_templates/*.html`` templates, which can be overridden from the
content overlay (``SITE_CONTENT_DIR``).
"""

import logging
import time
from dataclasses import dataclass
from email.mime.image import MIMEImage

from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.mail import EmailMultiAlternatives
from django.http import Http404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from offrants.models import Offrant

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Campaign:
    key: str
    template: str
    url_name: str
    token_field: str
    sent_field: str
    opened_field: str
    main_color: str
    font_color: str
    subject_setting: str

    def get_guest_or_404(self, token):
        try:
            return Offrant.objects.get(**{self.token_field: token})
        except Offrant.DoesNotExist:
            raise Http404("Unknown link") from None

    def token_of(self, offrant):
        return getattr(offrant, self.token_field)

    def mark_opened(self, offrant):
        if getattr(offrant, self.opened_field) is None:
            setattr(offrant, self.opened_field, timezone.now())
            offrant.save(update_fields=[self.opened_field])

    def build_context(self, offrant=None):
        context = {
            "main_image": settings.EMAIL_HERO_IMAGE,
            "main_color": self.main_color,
            "font_color": self.font_color,
            "page_title": settings.SITE_TITLE,
            "preheader_text": settings.SITE_TITLE,
            "reply_address": settings.BIRTHLIST_REPLY_EMAIL,
            "site_url": settings.SITE_URL,
            "couple": settings.COUPLE_NAMES,
            "baby_name": settings.BABY_NAME,
            "url_name": self.url_name,
        }
        if offrant is not None:
            context.update(
                offrant=offrant,
                first_name=offrant.first_name,
                last_name=offrant.last_name,
                token=self.token_of(offrant),
                email_mode=True,
            )
        return context

    def render_preview(self):
        """Render the HTML e-mail for a browser, with a dummy token."""
        context = self.build_context()
        context["token"] = "0" * 32
        return render_to_string(self.template, context=context)

    def build_message(self, offrant):
        context = self.build_context(offrant)
        html = render_to_string(self.template, context=context)
        link = f"{settings.SITE_URL}{reverse(self.url_name, args=[self.token_of(offrant)])}"
        text = f"{settings.COUPLE_NAMES} - {settings.SITE_TITLE}\n\n{link}"
        message = EmailMultiAlternatives(
            getattr(settings, self.subject_setting),
            text,
            settings.DEFAULT_FROM_EMAIL,
            to=[offrant.email],
            cc=settings.BIRTHLIST_CC_LIST,
            reply_to=[settings.BIRTHLIST_REPLY_EMAIL] if settings.BIRTHLIST_REPLY_EMAIL else None,
        )
        message.attach_alternative(html, "text/html")
        message.mixed_subtype = "related"
        if settings.EMAIL_HERO_IMAGE:
            image_path = finders.find(settings.EMAIL_HERO_IMAGE)
            if image_path:
                with open(image_path, "rb") as image_file:
                    image = MIMEImage(image_file.read())
                image.add_header("Content-ID", f"<{settings.EMAIL_HERO_IMAGE}>")
                message.attach(image)
            else:
                logger.warning("E-mail image %s not found in static files", settings.EMAIL_HERO_IMAGE)
        return message

    def send_all(self, send=False, mark_sent=False, delay=0.0, stdout=None):
        """Send the campaign to every guest it has not been sent to yet.

        Nothing is sent unless ``send`` is true. Guests are only marked as sent after the message was
        really handed to the mail backend; a failure for one guest does not stop the others.
        Returns ``(sent, failed)``.
        """
        write = stdout.write if stdout else print
        sent = failed = 0
        for offrant in Offrant.objects.filter(**{self.sent_field: None}).exclude(email=""):
            message = self.build_message(offrant)
            if not send:
                write(f"[dry-run] {self.key}: would send to {offrant.email}")
                continue
            try:
                message.send()
            except Exception:
                logger.exception("Could not send %s to %s", self.key, offrant.email)
                failed += 1
                continue
            sent += 1
            write(f"{self.key}: sent to {offrant.email}")
            if mark_sent:
                setattr(offrant, self.sent_field, timezone.now())
                offrant.save(update_fields=[self.sent_field])
            if delay:
                time.sleep(delay)
        return sent, failed

    def reset_sent(self):
        return Offrant.objects.exclude(**{self.sent_field: None}).update(**{self.sent_field: None})


ANNOUNCEMENT = Campaign(
    key="announcement",
    template="offrants/email_templates/announcement.html",
    url_name="rsvp",
    token_field="rsvp_id",  # noqa: S106
    sent_field="rsvp_sent",
    opened_field="rsvp_opened",
    main_color="#fff3e8",
    font_color="#666666",
    subject_setting="ANNOUNCEMENT_SUBJECT",
)
NOTICE = Campaign(
    key="notice",
    template="offrants/email_templates/notice.html",
    url_name="invitation",
    token_field="invitation_id",  # noqa: S106
    sent_field="invitation_sent",
    opened_field="invitation_opened",
    main_color="#ffffff",
    font_color="#000000",
    subject_setting="NOTICE_SUBJECT",
)
CAMPAIGNS = {c.key: c for c in (ANNOUNCEMENT, NOTICE)}
