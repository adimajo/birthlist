from django.core.validators import MinValueValidator
from django.db import models

from offrants.models import Offrant


class Cadeau(models.Model):
    """A gift of the birth list."""

    name = models.CharField("nom", max_length=200)
    photo = models.URLField(blank=True)
    link = models.URLField(blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField("prix", decimal_places=2, max_digits=10, validators=[MinValueValidator(0)])
    interested_families = models.ManyToManyField(Offrant, related_name="interested", blank=True)
    bought_by = models.ManyToManyField(Offrant, related_name="bought", blank=True)

    class Meta:
        verbose_name_plural = "Cadeaux"
        ordering = ["id"]

    def __str__(self):
        return self.name
