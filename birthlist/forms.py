from django import forms
from django.conf import settings
from django.contrib.auth.forms import PasswordResetForm, UserCreationForm
from django.utils.crypto import constant_time_compare

from offrants.models import Offrant


class RegisterForm(UserCreationForm):
    """Account creation, only for people who know the shared registration code."""

    first_name = forms.CharField(label="Prénom", max_length=150)
    last_name = forms.CharField(label="Nom", max_length=150)
    email = forms.EmailField(label="Email")
    registration_code = forms.CharField(
        label="Code d'accès",
        help_text="Le code figure dans le message que vous avez reçu de notre part.",
        strip=True,
    )

    class Meta:
        model = Offrant
        fields = ["first_name", "last_name", "email", "password1", "password2"]

    def clean_registration_code(self):
        code = self.cleaned_data["registration_code"]
        expected = settings.REGISTRATION_CODE
        if not expected or not constant_time_compare(code.casefold(), expected.casefold()):
            raise forms.ValidationError("Code d'accès incorrect.")
        return code

    def clean_email(self):
        email = Offrant.objects.normalize_email(self.cleaned_data["email"])
        if Offrant.objects.filter(email__iexact=email, is_active=True).exists():
            raise forms.ValidationError(
                "Un compte existe déjà avec cet email : connectez-vous ou réinitialisez votre mot de passe."
            )
        return email


class GuestPasswordResetForm(PasswordResetForm):
    """Password reset that also works for guests imported without a password."""

    def get_users(self, email):
        return Offrant.objects.filter(email__iexact=email, is_active=True)

    def save(self, *args, extra_email_context=None, **kwargs):
        # Built from the settings at call time (the proxy-provided Host header is not trusted for links).
        extra_email_context = {
            **(extra_email_context or {}),
            "site_title": settings.SITE_TITLE,
            "site_url": settings.SITE_URL,
        }
        return super().save(*args, extra_email_context=extra_email_context, **kwargs)
