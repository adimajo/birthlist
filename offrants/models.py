import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


def _random_uuid():
    return uuid.uuid4().hex


class OffrantManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, first_name, last_name, email, password=None, **extra_fields):
        """Create a guest. Without a password the account can only be used through its personal links."""
        if not email:
            raise ValueError("A guest must have an email address")
        user = self.model(first_name=first_name, last_name=last_name, email=self.normalize_email(email), **extra_fields)
        if password is None:
            user.set_unusable_password()
        else:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, first_name, last_name, email, password=None, **extra_fields):
        extra_fields["is_staff"] = True
        extra_fields["is_superuser"] = True
        return self.create_user(first_name, last_name, email, password, **extra_fields)


class Offrant(AbstractBaseUser, PermissionsMixin):
    """
    A guest able to offer a gift.

    ``invitation_id`` and ``rsvp_id`` are secret tokens embedded in the personal links of the
    two e-mail campaigns ("annonce" and "faire-part"); opening one of them logs the guest in.
    """

    id = models.CharField(max_length=32, default=_random_uuid, primary_key=True, editable=False)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    created = models.DateTimeField(default=timezone.now, editable=False)
    invitation_id = models.CharField(max_length=32, db_index=True, default=_random_uuid, unique=True, editable=False)
    invitation_sent = models.DateTimeField(null=True, blank=True, default=None)
    invitation_opened = models.DateTimeField(null=True, blank=True, default=None)
    rsvp_id = models.CharField(max_length=32, db_index=True, default=_random_uuid, unique=True, editable=False)
    rsvp_sent = models.DateTimeField(null=True, blank=True, default=None)
    rsvp_opened = models.DateTimeField(null=True, blank=True, default=None)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    REQUIRED_FIELDS = ["first_name", "last_name"]
    USERNAME_FIELD = "email"
    objects = OffrantManager()

    class Meta:
        verbose_name = "invité"
        verbose_name_plural = "invités"
        ordering = ["first_name", "last_name"]

    @property
    def name(self):
        return f"{self.first_name} {self.last_name}"

    def get_full_name(self):
        return self.name

    def get_short_name(self):
        return self.first_name

    def __str__(self):
        return self.name
