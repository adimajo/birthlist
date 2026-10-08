from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import connection
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import ListView

from birthlist.forms import RegisterForm
from birthlist.models import Cadeau

SORT_FIELDS = {"id", "name", "price"}


@require_GET
def healthz(request):
    """Liveness/readiness probe used by the container healthcheck."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return HttpResponse("ok", content_type="text/plain")


def register_request(request):
    if not settings.REGISTRATION_CODE:
        raise Http404("Registration is disabled")
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            messages.success(request, "Votre compte a bien été créé.")
            return redirect("home")
        messages.error(request, "Inscription impossible : merci de corriger les erreurs ci-dessous.")
    else:
        form = RegisterForm()
    return render(request, "register.html", {"register_form": form})


class Accueil(LoginRequiredMixin, ListView):
    """The gift list, sortable by id (default), name or price."""

    template_name = "home.html"
    context_object_name = "gifts"

    def get_ordering_params(self):
        order_by = self.request.GET.get("order_by", "id")
        if order_by not in SORT_FIELDS:
            order_by = "id"
        descending = self.request.GET.get("direction") == "desc"
        return order_by, descending

    def get_queryset(self):
        order_by, descending = self.get_ordering_params()
        return Cadeau.objects.prefetch_related("interested_families", "bought_by").order_by(
            f"-{order_by}" if descending else order_by
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order_by, descending = self.get_ordering_params()
        context["order_by"] = order_by
        context["next_direction"] = "asc" if descending else "desc"
        return context


def _toggle(request, pk, relation, add):
    gift = get_object_or_404(Cadeau, pk=pk)
    manager = getattr(gift, relation)
    if add:
        manager.add(request.user)
    else:
        manager.remove(request.user)
    return redirect(f"{reverse('home')}#gift-{gift.pk}")


@login_required
@require_POST
def declare_interest(request, pk):
    return _toggle(request, pk, "interested_families", add=True)


@login_required
@require_POST
def declare_not_interested(request, pk):
    return _toggle(request, pk, "interested_families", add=False)


@login_required
@require_POST
def declare_bought(request, pk):
    return _toggle(request, pk, "bought_by", add=True)


@login_required
@require_POST
def declare_not_bought(request, pk):
    return _toggle(request, pk, "bought_by", add=False)
