from django.urls import path

from offrants import views

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("invite/<str:token>/", views.invitation, name="invitation"),
    path("rsvp/<str:token>/", views.rsvp, name="rsvp"),
    path("invite-email/", views.invitation_email_preview, name="invitation-email"),
    path("rsvp-email/", views.rsvp_email_preview, name="rsvp-email"),
    path("invite-email-test/", views.invitation_email_test, name="invitation-email-test"),
    path("rsvp-email-test/", views.rsvp_email_test, name="rsvp-email-test"),
]
