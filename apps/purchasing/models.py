import re

from django.core.validators import MinLengthValidator
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.core.models import AuditModel
from apps.security.utils.validators import django_id_validator


class Supplier(AuditModel):
    """Represents a Supplier entity."""

    business_name = models.CharField(_("Business name"), max_length=200)
    reason = models.CharField(_("Reason"), max_length=100)
    tax_id = models.CharField(
        _("Tax id"),
        max_length=13,
        validators=[MinLengthValidator(10), django_id_validator],
    )
    delivery_days = models.IntegerField(_("Delivery days"), default=0)

    # Contact information
    email = models.EmailField(_("Email address"), unique=True, max_length=255)
    phone = models.CharField(_("Phone number"), max_length=15, validators=[MinLengthValidator(10)])

    class Meta:
        db_table = "supplier"
        verbose_name = _("Supplier")
        verbose_name_plural = _("Suppliers")
        ordering = ("-created_at",)

    def __str__(self):
        return self.reason

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
        return reverse("purchasing:suppliers:detail", kwargs={"external_id": self.external_id})


class PurchaseOrder(AuditModel):
    """Purchase order for supplies."""

    class Status(models.IntegerChoices):
        DRAFT = 0, _("Draft")
        SENT = 1, _("Sent")
        COMPLETED = 2, _("Completed")
        CANCELLED = 3, _("Cancelled")

    order_number = models.CharField(_("Order number"), max_length=50, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="purchase_orders")
    status = models.PositiveSmallIntegerField(_("Status"), choices=Status, default=Status.DRAFT)

    class Meta:
        db_table = "purchase_order"
        verbose_name = _("Purchase Order")
        verbose_name_plural = _("Purchase Orders")
        ordering = ["-created_at"]

    def __str__(self):
        return f"PO #{self.order_number} - {self.supplier.business_name}"


class OrderDetail(AuditModel):
    """Purchase order line items."""

    order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="details")
    supply = models.ForeignKey("inventory.Supply", on_delete=models.PROTECT, related_name="details")
    quantity_requested = models.PositiveIntegerField(_("Quantity requested"), default=0)
    quantity_received = models.PositiveIntegerField(_("Quantity received"), default=0)
    unit_cost = models.DecimalField(_("Unit cost"), max_digits=10, decimal_places=2)

    class Meta:
        db_table = "order_detail"
        unique_together = [["order", "supply"]]
        verbose_name = _("Order detail")
        verbose_name_plural = _("Order details")
