from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from offrants.models import Offrant


@admin.register(Offrant)
class OffrantAdmin(UserAdmin):
    list_display = ("first_name", "last_name", "email", "invitation_opened", "rsvp_opened", "is_staff")
    list_filter = ("is_staff", "is_superuser")
    search_fields = ("first_name", "last_name", "email")
    ordering = ("first_name", "last_name")
    readonly_fields = ("created", "invitation_id", "rsvp_id")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Identité", {"fields": ("first_name", "last_name", "created")}),
        (
            "Campagnes",
            {
                "fields": (
                    "rsvp_id",
                    "rsvp_sent",
                    "rsvp_opened",
                    "invitation_id",
                    "invitation_sent",
                    "invitation_opened",
                )
            },
        ),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("first_name", "last_name", "email", "password1", "password2")}),
    )
