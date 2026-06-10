from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.core.models import AuditModel


class BaseOrder(AuditModel):
    motive = models.TextField(_("Motive"), blank=True, null=True)
    order_number = models.CharField(_("Order number"), max_length=50, unique=True)
    observations = models.TextField(_("Observations"), blank=True, null=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f"Order #{self.order_number}"


class BaseOrderDetail(AuditModel):
    quantity_requested = models.PositiveIntegerField(
        _("Quantity requested"), default=0, validators=[MinValueValidator(1)]
    )
    unit_cost = models.DecimalField(_("Unit cost"), max_digits=12, decimal_places=2)

    class Meta:
        abstract = True


class PurchaseOrder(BaseOrder):
    ORDER_PREFIX = "IN"

    class Status(models.IntegerChoices):
        DRAFT = 0, _("Draft")
        SENT = 1, _("Sent")
        COMPLETED = 2, _("Completed")
        CANCELLED = 3, _("Cancelled")

        @property
        def ui_config(self):
            configs = {
                self.DRAFT: {"color": "secondary", "icon": "bi bi-pencil"},
                self.SENT: {"color": "info", "icon": "bi bi-send"},
                self.COMPLETED: {"color": "success", "icon": "bi bi-check-lg"},
                self.CANCELLED: {"color": "danger", "icon": "bi bi-x-lg"},
            }
            return configs.get(self, {"color": "secondary", "icon": "bi bi-question"})

        @property
        def color(self):
            return self.ui_config["color"]

        @property
        def icon(self):
            return self.ui_config["icon"]

        @classmethod
        def get_ui_map(cls):
            return {
                item.value: {"color": item.color, "icon": item.icon, "label": item.label}
                for item in cls
            }

    estimated_delivery = models.DateTimeField(_("Estimated delivery"), null=True, blank=True)
    actual_delivery = models.DateField(_("Actual delivery"), null=True, blank=True)
    status = models.PositiveSmallIntegerField(_("Status"), choices=Status, default=Status.DRAFT)
    supplier = models.ForeignKey(
        "operations.Supplier",
        on_delete=models.PROTECT,
        related_name="purchase_orders",
        verbose_name=_("Supplier"),
    )

    class Meta:
        db_table = "purchase_order"
        verbose_name = _("Purchase Order")
        verbose_name_plural = _("Purchase Orders")
        ordering = ["-created_at"]

    def __str__(self):
        return f"PO #{self.order_number} - {self.supplier.business_name}"

    def get_absolute_url(self):
        return reverse("operations:inbound_order:detail", kwargs={"external_id": self.external_id})

    @property
    def total(self):
        return sum(detail.line_total for detail in self.details.all())

    @property
    def total_requested(self):
        return (
            self.details.filter(deleted_at__isnull=True).aggregate(
                total=models.Sum("quantity_requested")
            )["total"]
            or 0
        )

    @property
    def lines_received(self):
        return self.details.filter(deleted_at__isnull=True, quantity_received__gt=0).count()

    @property
    def total_received(self):
        return (
            self.details.filter(deleted_at__isnull=True).aggregate(
                total=models.Sum("quantity_received")
            )["total"]
            or 0
        )

    @property
    def percentage_received(self):
        if self.total_requested == 0:
            return 0
        return int((self.total_received / self.total_requested) * 100)

    @property
    def color(self):
        return self.Status(self.status).color


class PurchaseOrderDetail(BaseOrderDetail):
    quantity_received = models.PositiveIntegerField(_("Quantity received"), default=0)
    observations = models.TextField(blank=True, null=True)
    unit_cost = models.DecimalField(
        _("Unit cost"), max_digits=12, decimal_places=2, validators=[MinValueValidator(0.1)]
    )

    # Relationships
    order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="details")
    supply = models.ForeignKey(
        "inventory.Supply", on_delete=models.PROTECT, related_name="purchase_order_details"
    )
    batch = models.ForeignKey(
        "inventory.Batch",
        on_delete=models.PROTECT,
        related_name="purchase_order_details",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "purchase_order_detail"
        unique_together = [["order", "supply", "batch"]]

    def clean(self):
        cleaned_data = super().clean()
        requested = self.quantity_requested
        received = self.quantity_received

        if requested is not None and received is not None:
            if received > requested:
                raise ValidationError(
                    {"quantity_received": _("Quantity received cannot be greater than requested.")}
                )

        if received < 0:
            raise ValidationError({"quantity_received": _("Quantity received cannot be negative.")})
        return cleaned_data

    @property
    def line_total(self):
        return self.quantity_received * self.unit_cost

    @property
    def is_complete(self):
        return self.quantity_received >= self.quantity_requested

    @property
    def percentage(self):
        if self.quantity_requested == 0:
            return 0
        return int((self.quantity_received / self.quantity_requested) * 100)


class ExitOrder(BaseOrder):
    ORDER_PREFIX = "OU"

    class Status(models.IntegerChoices):
        DRAFT = 0, _("Draft")
        COMPLETED = 1, _("Completed")
        CANCELLED = 2, _("Cancelled")

    class StatusColor(models.IntegerChoices):
        DRAFT = 0, "secondary"
        COMPLETED = 1, "success"
        CANCELLED = 2, "danger"

    status = models.SmallIntegerField(_("Status"), default=Status.DRAFT, choices=Status)
    requested_by = models.CharField(_("Requested by"), max_length=150, null=True, blank=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    class Meta:
        db_table = "exit_order"
        verbose_name = _("Exit Order")
        verbose_name_plural = _("Exit Orders")
        ordering = ["-created_at"]

    def get_absolute_url(self):
        return reverse("operations:outbound_order:detail", kwargs={"external_id": self.external_id})

    def recalculate_totals(self):
        details = self.details.all()
        self.subtotal = sum(d.quantity_requested * d.unit_cost for d in details)
        self.total = self.subtotal

    @property
    def get_status_color(self):
        return self.StatusColor(self.status).label

    @property
    def get_status_display(self):
        return self.Status(self.status).label


class ExitDetail(BaseOrderDetail):
    quantity_dispatched = models.PositiveIntegerField(_("Quantity dispatched"), default=0)

    supply = models.ForeignKey(
        "inventory.Supply", on_delete=models.PROTECT, related_name="exit_details"
    )
    batch = models.ForeignKey(
        "inventory.Batch", on_delete=models.PROTECT, related_name="exit_details"
    )
    order = models.ForeignKey(ExitOrder, on_delete=models.CASCADE, related_name="details")

    class Meta:
        db_table = "exit_detail"
        ordering = ["quantity_requested", "-created_at"]
        unique_together = [["order", "supply", "batch"]]

    @property
    def line_total(self):
        quantity = self.quantity_dispatched or self.quantity_requested
        return quantity * self.unit_cost
