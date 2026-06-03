import re

from django.core.validators import MinLengthValidator
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.core.models import AuditModel
from apps.security.utils.validators import django_id_validator


class Supplier(AuditModel):
    """Represents a Supplier entity."""

    tax_id = models.CharField(
        _("RUC / DNI"),
        max_length=13,
        unique=True,
        validators=[MinLengthValidator(10), django_id_validator],
    )
    contact_name = models.CharField(_("Contact name"), max_length=255)
    business_name = models.CharField(_("Business name"), max_length=200)
    delivery_days = models.PositiveIntegerField(_("Delivery days"), default=0)
    # Contact information
    email = models.EmailField(_("Email address"), unique=True, max_length=255)
    phone = models.CharField(_("Phone number"), max_length=15, validators=[MinLengthValidator(10)])
    address = models.CharField(_("Address"), blank=True, null=True)

    class Meta:
        db_table = "supplier"
        verbose_name = _("Supplier")
        verbose_name_plural = _("Suppliers")
        ordering = ("business_name",)

    def __str__(self):
        return f"{self.business_name} ({self.tax_id})"

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
