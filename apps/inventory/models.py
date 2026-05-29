from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.catalogs.models import Catalog
from apps.core.models import AuditModel


class Supply(AuditModel):
    """Represents a supply item in the system."""

    name = models.CharField(_("Name"), max_length=255)
    code = models.CharField(_("Code"), max_length=50)
    description = models.CharField(_("Description"), max_length=255)
    image_url = models.ImageField(_("Image URL"), upload_to="supplies/")
    stock_min = models.PositiveIntegerField(_("Stock min"), default=10)

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
        ordering = ("name", "-created_at")

    def __str__(self):
        return self.name


class Batch(AuditModel):
    """Represents a batch of supplies, defining its properties, state, and related information."""

    class Status(models.IntegerChoices):
        DISCARDED = 0, _("Discarded")
        ACTIVE = 1, _("Active")
        EXPIRED = 2, _("Expired")

    supply = models.ForeignKey(
        Supply, verbose_name=_("Supply"), on_delete=models.PROTECT, related_name="batches"
    )
    number = models.CharField(_("Number"), max_length=100)
    expiration_date = models.DateField(_("Expiration date"))
    stock = models.PositiveIntegerField(
        _("Stock"), default=0, validators=[MinValueValidator(0)]
    )  # stock actual
    purchase_unit_cost = models.DecimalField(
        _("Purchase unit cost"), max_digits=10, decimal_places=2
    )
    status = models.PositiveIntegerField(_("Status"), choices=Status, default=Status.ACTIVE)
    purchase_order = models.ForeignKey(
        "purchasing.PurchaseOrder",
        verbose_name=_("Purchase order"),
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    class Meta:
        db_table = "batch"
        verbose_name = _("Batch")
        verbose_name_plural = _("Batches")
        ordering = (
            "number",
            "-expiration_date",
        )
        unique_together = (("supply", "number"),)

    def __str__(self):
        return f"{self.supply.name} - {self.number}"

    @property
    def is_expired(self):
        return self.expiration_date < timezone.now().date()


class InventoryMovement(AuditModel):
    """Represents an inventory movement with details about the transaction type, concept, quantity,
    and its effect on stock levels.
    """

    class Type(models.IntegerChoices):
        INBOUND = 0, _("Inbound")
        OUTBOUND = 1, _("Outbound")
        ADJUSTMENT = 2, _("Adjustment")

    batch = models.ForeignKey(
        Batch, verbose_name=_("Batch"), on_delete=models.PROTECT, related_name="movements"
    )
    movement_type = models.PositiveSmallIntegerField(_("Type"), choices=Type)
    concept = models.CharField(_("Concept"), max_length=255)
    quantity = models.PositiveIntegerField(_("Quantity"), validators=[MinValueValidator(0)])
    observation = models.CharField(_("Observation"), max_length=255)
    previous_stock = models.PositiveIntegerField(
        _("Previous stock"), validators=[MinValueValidator(0)], default=0
    )
    after_stock = models.PositiveIntegerField(_("After stock"), validators=[MinValueValidator(0)])
    is_increment = models.BooleanField(_("Increment"), blank=True, null=True)

    class Meta:
        db_table = "inventory_movement"
        verbose_name = _("Inventory Movement")
        verbose_name_plural = _("Inventory Movements")
        ordering = ["-created_at"]

    def __str__(self):
        return self.get_movement_type_display()

    @transaction.atomic
    def save(self, *args, **kwargs):
        if not self.pk:
            self.previous_stock = self.batch.stock
            if self.movement_type == self.Type.INBOUND:
                self.batch.stock += self.quantity
            elif self.movement_type == self.Type.OUTBOUND:
                self.batch.stock -= self.quantity
            elif self.movement_type == self.Type.ADJUSTMENT:
                if getattr(self, "is_increment", False):
                    self.batch.stock += self.quantity
                else:
                    self.batch.stock -= self.quantity

            self.after_stock = self.batch.stock

            self.batch.save()

        super().save(*args, **kwargs)
