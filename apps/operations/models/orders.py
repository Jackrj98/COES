from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import AuditModel


class BaseOrder(AuditModel):
    """Model for purchase orders and exit orders."""

    order_number = models.CharField(_("Order number"), max_length=50, unique=True)
    observations = models.TextField(_("Observations"), blank=True, null=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f"Order #{self.order_number}"


class BaseOrderDetail(AuditModel):
    """Model for order details and exit details."""

    quantity_requested = models.PositiveIntegerField(_("Quantity requested"), default=0)
    quantity_received = models.PositiveIntegerField(_("Quantity received"), default=0)
    unit_cost = models.DecimalField(_("Unit cost"), max_digits=10, decimal_places=2)

    @property
    def line_total(self):
        return self.quantity_received * self.unit_cost

    class Meta:
        abstract = True


class PurchaseOrder(BaseOrder):
    """Represents a Purchase Order entity."""

    class Status(models.IntegerChoices):
        DRAFT = 0, _("Draft")
        SENT = 1, _("Sent")
        COMPLETED = 2, _("Completed")
        CANCELLED = 3, _("Cancelled")

    estimated_delivery = models.DateTimeField(_("Estimated delivery"), null=True, blank=True)
    actual_delivery = models.DateField(_("Actual delivery"), null=True, blank=True)
    status = models.PositiveSmallIntegerField(_("Status"), choices=Status, default=Status.DRAFT)
    # Relationships
    supplier = models.ForeignKey(
        "Supplier", on_delete=models.PROTECT, related_name="purchase_orders"
    )

    class Meta:
        db_table = "purchase_order"
        verbose_name = _("Purchase Order")
        verbose_name_plural = _("Purchase Orders")
        ordering = ["-created_at"]

    def __str__(self):
        return f"PO #{self.order_number} - {self.supplier.business_name}"


class OrderDetail(BaseOrderDetail):
    """Purchase order line items."""

    order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="details")
    supply = models.ForeignKey("inventory.Supply", on_delete=models.PROTECT, related_name="details")

    class Meta:
        db_table = "order_detail"
        verbose_name = _("Order detail")
        verbose_name_plural = _("Order details")
        unique_together = [["order", "supply"]]
        ordering = ["-created_at"]


class ExitOrder(BaseOrder):
    class Status(models.IntegerChoices):
        DRAFT = 0, _("Draft")
        PENDING = 1, _("Pending")
        APPROVED = 2, _("Approved")
        REJECTED = 3, _("Rejected")
        CANCELLED = 4, _("Cancelled")
        COMPLETED = 5, _("Completed")

    status = models.SmallIntegerField(_("Status"), default=1, choices=Status)
    processed_by = models.CharField(_("Processed by"), max_length=255, blank=True)
    reject_reason = models.TextField(_("Reject reason"), blank=True, null=True)

    @property
    def total(self):
        return sum(detail.line_total for detail in self.details.all())

    class Meta:
        db_table = "exit_order"
        verbose_name = _("Exit order")
        verbose_name_plural = _("Exit orders")


class ExitDetail(BaseOrderDetail):
    """Exit order line items."""

    supply = models.ForeignKey(
        "inventory.Supply", on_delete=models.CASCADE, related_name="exit_details"
    )
    exit_order = models.ForeignKey(ExitOrder, on_delete=models.CASCADE, related_name="details")

    class Meta:
        db_table = "exit_detail"
        verbose_name = _("Exit detail")
        verbose_name_plural = _("Exit details")
        unique_together = [["exit_order", "supply"]]
        ordering = ["-created_at"]
