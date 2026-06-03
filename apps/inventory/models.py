from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.catalogs.models import Catalog
from apps.core.models import AuditModel
from apps.core.utils.helpers import generate_upload_path
from apps.inventory.choices import BatchStatus, InventoryMovementStatus, InventoryMovementType


class Supply(AuditModel):
    """Represents a supply item in the system."""

    name = models.CharField(_("Name"), max_length=255)
    code = models.CharField(
        _("Code"),
        max_length=50,
        unique=True,
        db_index=True,
        help_text=_("Unique identifier code, numbers and underscores"),
    )
    description = models.CharField(_("Description"), max_length=255)
    image_url = models.ImageField(
        _("Image URL"), upload_to=generate_upload_path, blank=True, null=True
    )
    stock_min = models.PositiveIntegerField(
        _("Stock min"), default=10, help_text=_("Notify me when stock reaches this level")
    )

    category = models.ForeignKey(
        "catalogs.CatalogItem",
        on_delete=models.PROTECT,
        related_name="supplies_by_category",
        verbose_name=_("Category"),
        limit_choices_to={"catalog__code": Catalog.CatalogCodes.SUPPLY_CATEGORY},
        null=True,
        blank=True,
    )

    unit_of_measure = models.ForeignKey(
        "catalogs.CatalogItem",
        on_delete=models.PROTECT,
        related_name="supplies_by_unit",
        verbose_name=_("Unit of Measure"),
        limit_choices_to={"catalog__code": Catalog.CatalogCodes.UNIT_OF_MEASURE},
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "supply"
        verbose_name = _("Supply")
        verbose_name_plural = _("Supplies")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} - {self.code}"

    def get_absolute_url(self):
        return reverse("inventory:supplies:detail", kwargs={"external_id": self.external_id})

    @property
    def stock_available(self):
        return self.batches.aggregate(models.Sum("stock"))["stock__sum"] or 0

    @property
    def stock_min_reached(self):
        return self.stock_available <= self.stock_min

    @property
    def initials(self):
        name_parts = self.name.split()
        initials = "".join(part[0] for part in name_parts[:2])
        return initials.upper()

    @property
    def active_batches(self):
        return self.batches.filter(status=Batch.Status.ACTIVE).count()

    @property
    def stock_percentage(self):
        if self.stock_min <= 0:
            return 0

        pct = (self.stock_available / self.stock_min) * 100
        return min(round(pct), 100)

    @property
    def color(self):
        current_stock = getattr(self, "total_stock", self.stock_available) or 0
        if current_stock >= self.stock_min:
            return "success"
        elif current_stock > self.stock_min * 0.2:
            return "warning"
        else:
            return "danger"

    def get_image(self):
        """Get the URL of the user's image."""
        if self.image_url:
            return f"{settings.MEDIA_URL}{self.image_url}"
        return f"{settings.STATIC_URL}assets/img/undraw_profile.svg"


class Batch(AuditModel):
    """Represents a batch of supplies, defining its properties, state, and related information."""

    # Choices
    Status = BatchStatus

    # Fields
    number = models.CharField(_("Number"), max_length=100)
    due_date = models.DateField(_("Due date"), null=True, blank=True)
    stock = models.PositiveIntegerField(
        _("Stock"), default=0, validators=[MinValueValidator(0)]
    )  # stock actual
    purchase_unit_cost = models.DecimalField(
        _("Purchase unit cost"), max_digits=10, decimal_places=2
    )
    status = models.PositiveIntegerField(_("Status"), choices=Status, default=Status.ACTIVE)

    # Relationships
    supply = models.ForeignKey(
        Supply,
        verbose_name=_("Supply"),
        on_delete=models.PROTECT,
        related_name="batches",
        null=True,
        blank=True,
    )
    purchase_order = models.ForeignKey(
        "operations.PurchaseOrder",
        verbose_name=_("Purchase order"),
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    class Meta:
        db_table = "batch"
        verbose_name = _("Batch")
        verbose_name_plural = _("Batches")
        ordering = ["-due_date"]
        unique_together = (("supply", "number"),)

    def __str__(self):
        return f"{self.supply.name} - {self.number}"

    def get_absolute_url(self):
        kwargs = {"supply_reference": self.supply.external_id, "external_id": self.external_id}
        return reverse("inventory:batches:detail", kwargs=kwargs)

    @property
    def is_expired(self):
        return self.due_date < timezone.now().date()

    @property
    def days_until_expiry(self):
        if not self.due_date:
            return None

        delta = self.due_date - timezone.now().date()
        return delta.days

    @property
    def batch_total_cost(self):
        return round(self.stock * self.purchase_unit_cost, 2)

    @property
    def color(self):
        return self.Status(self.status).color


class DocumentMovement(AuditModel):
    """Polymorphic table linking movements to their source documents."""

    DOCUMENT_TYPES = [
        ("PURCHASE_ORDER", _("Purchase Order")),
        ("EXIT_ORDER", _("Exit Order")),
        ("MANUAL", _("Manual Adjustment")),
    ]

    document_type = models.CharField(_("Document type"), max_length=30, choices=DOCUMENT_TYPES)
    document_id = models.PositiveIntegerField(_("Document ID"))
    observations = models.TextField(_("Observations"), blank=True)

    class Meta:
        db_table = "document_movement"
        verbose_name = _("Document Movement")
        verbose_name_plural = _("Document Movements")
        unique_together = [["document_type", "document_id"]]


class InventoryMovement(AuditModel):
    """Represents an inventory movement with details about the transaction type, concept, quantity,
    and its effect on stock levels.
    """

    # Choices
    Type = InventoryMovementType
    Status = InventoryMovementStatus

    # Fields
    movement_date = models.DateField(_("Movement date"), default=timezone.localdate)
    movement_type = models.PositiveSmallIntegerField(_("Type"), choices=Type)
    status = models.PositiveSmallIntegerField(_("Status"), choices=Status, default=Status.COMPLETED)
    concept = models.CharField(_("Concept"), max_length=255)
    quantity = models.PositiveIntegerField(_("Quantity"), validators=[MinValueValidator(0)])
    observation = models.CharField(_("Observation"), max_length=255)
    # Stock tracking
    previous_stock = models.PositiveIntegerField(_("Previous stock"), default=0)
    after_stock = models.PositiveIntegerField(_("After stock"), default=0)
    is_increment = models.BooleanField(_("Increment"), editable=False)
    unit_cost_at_movement = models.DecimalField(
        _("Unit cost at movement"), max_digits=10, decimal_places=2, null=True, blank=True
    )

    # Relationships
    batch = models.ForeignKey(
        Batch, verbose_name=_("Batch"), on_delete=models.PROTECT, related_name="movements"
    )
    document_movement = models.ForeignKey(
        DocumentMovement, on_delete=models.SET_NULL, null=True, blank=True, related_name="movements"
    )

    class Meta:
        db_table = "inventory_movement"
        verbose_name = _("Inventory Movement")
        verbose_name_plural = _("Inventory Movements")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["batch", "-created_at"]),
            models.Index(fields=["movement_type", "status"]),
        ]

    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.batch} - {self.quantity}"

    def save(self, *args, **kwargs):
        """Calculate previous_stock, after_stock, and is_increment."""
        if not self.pk:
            self.previous_stock = self.batch.stock

            if self.movement_type in [self.Type.INBOUND, self.Type.ADJUSTMENT]:
                self.is_increment = True
                self.after_stock = self.previous_stock + self.quantity
            else:
                self.is_increment = False
                self.after_stock = max(0, self.previous_stock - self.quantity)

            self.unit_cost_at_movement = self.batch.purchase_unit_cost

            self.batch.stock = self.after_stock
            self.batch.save(update_fields=["stock"])

        super().save(*args, **kwargs)
