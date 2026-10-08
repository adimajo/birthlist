from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from offrants.campaigns import ANNOUNCEMENT, NOTICE
from offrants.models import Offrant

BACKEND = "django.contrib.auth.backends.ModelBackend"


def _magic_link_view(campaign):
    def view(request, token):
        offrant = campaign.get_guest_or_404(token)
        campaign.mark_opened(offrant)
        login(request, offrant, backend=BACKEND)
        return redirect("home")

    view.__name__ = f"{campaign.key}_link"
    return view


# Personal links found in the e-mails: opening one logs the guest in.
invitation = _magic_link_view(NOTICE)
rsvp = _magic_link_view(ANNOUNCEMENT)


@staff_member_required
def dashboard(request):
    guests = Offrant.objects.order_by("first_name", "last_name")
    announcement_unopened = guests.filter(rsvp_opened=None)
    notice_unopened = guests.filter(invitation_opened=None)
    return render(
        request,
        "offrants/dashboard.html",
        context={
            "guest_count": guests.count(),
            "announcement_unopened": announcement_unopened,
            "notice_unopened": notice_unopened,
        },
    )


def _preview(campaign):
    @staff_member_required
    def view(request):
        return HttpResponse(campaign.render_preview())

    view.__name__ = f"{campaign.key}_preview"
    return view


def _test_send(campaign):
    @staff_member_required
    @require_POST
    def view(request):
        """Send the campaign e-mail to the requesting staff member only."""
        message = campaign.build_message(request.user)
        message.cc = []
        message.send()
        return HttpResponse("sent!", content_type="text/plain")

    view.__name__ = f"{campaign.key}_test"
    return view


invitation_email_preview = _preview(NOTICE)
rsvp_email_preview = _preview(ANNOUNCEMENT)
invitation_email_test = _test_send(NOTICE)
rsvp_email_test = _test_send(ANNOUNCEMENT)
