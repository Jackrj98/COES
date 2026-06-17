from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django_celery_beat.utils import now

from apps.core.models import AuditModel

# ─────────────────────────────────────────────────────────────────────────────
# Order single table with type discriminator
# ─────────────────────────────────────────────────────────────────────────────


class InventoryOrder(AuditModel):
    """Unified order table.

    Replaces PurchaseOrder + ExitOrder with a single normalized entity.
    The `order_type` field acts as a discriminator:
      - INBOUND → purchase / restocking from supplier
      - OUTBOUND → dispatch / exit
      - REPLENISHMENT → internal restock between locations

    Shared fields live here. Type-specific logic lives in proxy models
    or services, not in extra tables.
    """

    class OrderType(models.IntegerChoices):
        INBOUND = 0, _("Inbound")
        OUTBOUND = 1, _("Outbound")
        REPLENISHMENT = 2, _("Replenishment")

    class StatusType(models.IntegerChoices):
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

    # ── Discriminator ────────────────────────────────────────────────────────
    order_type = models.PositiveSmallIntegerField(_("Order type"), choices=OrderType, db_index=True)

    # ── Common fields (all types) ─────────────────────────────────────────────
    order_number = models.CharField(_("Order number"), max_length=50, unique=True)
    status = models.PositiveSmallIntegerField(
        _("Status"), choices=StatusType, default=StatusType.DRAFT
    )
    motive = models.TextField(_("Motive"), max_length=500)
    observations = models.TextField(_("Observations"), blank=True, null=True)

    # ── INBOUND-only fields (null for other types) ────────────────────────────
    supplier = models.ForeignKey(
        "operations.Supplier",
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name=_("Supplier"),
        null=True,
        blank=True,
    )
    scheduled_date = models.DateField(
        _("Schedule date"),
        default=now().date(),
        help_text=_("The date the items are expected to arrive."),
    )
    received_date = models.DateField(
        _("Received date"),
        help_text=_("The date the items were received by the supplier."),
        blank=True,
        null=True,
    )

    class Meta:
        db_table = "inventory_order"
        verbose_name = _("Inventory Order")
        verbose_name_plural = _("Inventory Orders")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order_type", "status"]),
            models.Index(fields=["order_number"]),
        ]
        permissions = (
            ("view_inbound_orders", "Can view inbound order list"),
            ("view_outbound_orders", "Can view outbound order list"),
            ("view_replenishment_orders", "Can view replenishment order list"),
        )

    def __str__(self):
        return f"#{self.order_number} [{self.get_order_type_display()}]"

    def get_absolute_url(self):
        routes = {
            self.OrderType.INBOUND: "operations:inbound:detail",
            self.OrderType.OUTBOUND: "operations:outbound:detail",
            self.OrderType.REPLENISHMENT: "operations:replenishment:detail",
        }
        return reverse(routes[self.order_type], kwargs={"external_id": self.external_id})

    def clean(self):
        super().clean()
        print(self.get_status_display())
        if self.pk:
            instance = self.__class__.objects.get(pk=self.pk)
            if instance.status == InventoryOrder.StatusType.COMPLETED:
                raise ValidationError({"status": _("Completed orders cannot be modified.")})

        if self.order_type == self.OrderType.INBOUND and not self.supplier_id:
            raise ValidationError({"supplier": _("Inbound orders require a supplier.")})

        if self.order_type != self.OrderType.INBOUND and self.supplier_id:
            raise ValidationError({"supplier": _("Only inbound orders can have a supplier.")})

        if self.status == self.StatusType.SENT and self.order_type != self.OrderType.INBOUND:
            raise ValidationError({"status": _("Only inbound orders can have 'Sent' status.")})

    # ── Computed properties ───────────────────────────────────────────────────

    @property
    def total(self):
        return sum(d.line_total for d in self.details.filter(deleted_at__isnull=True))

    @property
    def total_requested(self):
        return (
            self.details.filter(deleted_at__isnull=True).aggregate(
                total=models.Sum("quantity_requested")
            )["total"]
            or 0
        )

    @property
    def total_fulfilled(self):
        """Generic: received (inbound) or dispatched (outbound/replenishment)."""
        return (
            self.details.filter(deleted_at__isnull=True).aggregate(
                total=models.Sum("quantity_fulfilled")
            )["total"]
            or 0
        )

    @property
    def percentage_fulfilled(self):
        if self.total_requested == 0:
            return 0
        return int((self.total_fulfilled / self.total_requested) * 100)

    @property
    def color(self):
        return self.StatusType(self.status).color

    @property
    def is_complete(self):
        return self.status == self.StatusType.COMPLETED


# ─────────────────────────────────────────────────────────────────────────────
# Proxy models — thin wrappers for type-specific query sets and URLs
# ─────────────────────────────────────────────────────────────────────────────


class InboundOrderManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(order_type=InventoryOrder.OrderType.INBOUND)


class InboundOrder(InventoryOrder):
    """Proxy for purchase/inbound orders. No extra table."""

    ORDER_PREFIX = "IN"
    objects = InboundOrderManager()

    class Meta:
        proxy = True
        verbose_name = _("Inbound Order")
        verbose_name_plural = _("Inbound Orders")

    def save(self, *args, **kwargs):
        self.order_type = InventoryOrder.OrderType.INBOUND
        super().save(*args, **kwargs)


class OutboundOrderManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(order_type=InventoryOrder.OrderType.OUTBOUND)


class OutboundOrder(InventoryOrder):
    """Proxy for exit/outbound orders. No extra table."""

    ORDER_PREFIX = "OU"
    objects = OutboundOrderManager()

    class Meta:
        proxy = True
        verbose_name = _("Outbound Order")
        verbose_name_plural = _("Outbound Orders")

    def save(self, *args, **kwargs):
        self.order_type = InventoryOrder.OrderType.OUTBOUND
        super().save(*args, **kwargs)


class ReplenishmentOrderManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(order_type=InventoryOrder.OrderType.REPLENISHMENT)


class ReplenishmentOrder(InventoryOrder):
    """Proxy for internal replenishment orders. No extra table."""

    ORDER_PREFIX = "RE"
    objects = ReplenishmentOrderManager()

    class Meta:
        proxy = True
        verbose_name = _("Replenishment Order")
        verbose_name_plural = _("Replenishment Orders")

    def save(self, *args, **kwargs):
        self.order_type = InventoryOrder.OrderType.REPLENISHMENT
        super().save(*args, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# OrderDetail a single normalized table for all lines
# ─────────────────────────────────────────────────────────────────────────────


class OrderDetail(AuditModel):
    """Unified order detail line.

    Replaces PurchaseOrderDetail + ExitDetail.

    `quantity_fulfilled` is the generic column that means:
      - quantity_received for INBOUND
      - quantity_dispatched for OUTBOUND / REPLENISHMENT

    The semantic is determined by the parent order type.
    One model, one table, no duplication.
    """

    # ── Relationships ─────────────────────────────────────────────────────────
    inventory_order = models.ForeignKey(
        InventoryOrder,
        on_delete=models.CASCADE,
        related_name="details",
        verbose_name=_("Order"),
    )
    supply = models.ForeignKey(
        "inventory.Supply",
        on_delete=models.PROTECT,
        related_name="order_details",
        verbose_name=_("Supply"),
    )
    batch = models.ForeignKey(
        "inventory.Batch",
        on_delete=models.PROTECT,
        related_name="order_details",
        verbose_name=_("Batch"),
        null=True,
        blank=True,
    )

    # ── Quantity fields ───────────────────────────────────────────────────────
    quantity_requested = models.PositiveIntegerField(
        _("Quantity requested"), default=0, validators=[MinValueValidator(1)]
    )
    quantity_fulfilled = models.PositiveIntegerField(
        _("Quantity fulfilled"),
        default=0,
        help_text=_("Received (inbound) or dispatched (outbound/replenishment)"),
    )

    # ── Cost ─────────────────────────────────────────────────────────────────
    unit_cost = models.DecimalField(_("Unit cost"), max_digits=12, decimal_places=2, default=0.00)

    # ── Optional per-line note ────────────────────────────────────────────────
    observations = models.TextField(_("Observations"), blank=True, null=True)

    class Meta:
        db_table = "order_detail"
        verbose_name = _("Order detail")
        verbose_name_plural = _("Order details")
        constraints = [
            models.UniqueConstraint(
                fields=["inventory_order", "supply", "batch"], name="unique_order_supply_batch"
            )
        ]
        ordering = ["inventory_order", "-created_at"]

    def __str__(self):
        return f"{self.inventory_order} — {self.supply} x{self.quantity_requested}"

    def clean(self):
        super().clean()

        if self.quantity_fulfilled:
            if self.quantity_fulfilled > self.quantity_requested:
                raise ValidationError(
                    {
                        "quantity_fulfilled": _(
                            "Fulfilled quantity cannot exceed requested quantity."
                        )
                    }
                )

            if self.quantity_fulfilled < 0:
                raise ValidationError(
                    {"quantity_fulfilled": _("Fulfilled quantity cannot be negative.")}
                )

        if self.batch and self.batch.supply != self.supply:
            raise ValidationError(
                {"batch": _("Batch must belong to the same supply as the order detail.")}
            )

    # ── Computed properties ───────────────────────────────────────────────────

    @cached_property
    def line_total(self):
        quantity = self.quantity_fulfilled or self.quantity_requested
        return quantity * self.unit_cost

    @property
    def is_complete(self):
        return self.quantity_fulfilled >= self.quantity_requested

    @property
    def percentage(self):
        if self.quantity_requested == 0:
            return 0
        return int((self.quantity_fulfilled / self.quantity_requested) * 100)
