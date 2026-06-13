import re

from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.security.models import Person


class Supplier(Person):
    """Represents a Supplier entity."""

    business_name = models.CharField(_("Business name"), max_length=200)
    delivery_days = models.PositiveIntegerField(_("Delivery days"), default=0)
    # Contact information
    email = models.EmailField(_("Email address"), unique=True, max_length=255)

    address = models.CharField(_("Address"), blank=True, null=True)

    class Meta:
        db_table = "supplier"
        verbose_name = _("Supplier")
        verbose_name_plural = _("Suppliers")
        ordering = ("business_name",)
        permissions = (("view_suppliers", "Can view suppliers list"),)

    def __str__(self):
        return f"{self.business_name} ({self.document_number})"

    @property
    def initials(self):
        if not self.business_name or not self.business_name.strip():
            return "?"

        # Split by spaces, hyphens, and underscores
        words = re.split(r"[\s\-_]+", self.business_name.strip())
        words = [w for w in words if w]  # Filter empty strings

        if not words:
            return "?"

        if len(words) == 1:
            word = words[0]
            initials = word[:2] if len(word) >= 2 else word[0] * 2
        else:
            initials = words[0][0] + words[-1][0]

        return initials.upper()

    def get_absolute_url(self):
        return reverse("operations:suppliers:detail", kwargs={"external_id": self.external_id})
