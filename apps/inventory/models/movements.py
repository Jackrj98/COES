from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import AuditModel
from apps.inventory.utils.choices import InventoryMovementStatus, InventoryMovementType


class InventoryMovement(AuditModel):
    """Represents an inventory movement with automatic stock tracking."""

    # Choices
    Type = InventoryMovementType
    MovementStatusChoices = InventoryMovementStatus

    # Fields
    concept = models.CharField(_("Concept"), max_length=255)
    movement_type = models.PositiveSmallIntegerField(_("Type"), choices=Type)
    quantity = models.PositiveIntegerField(_("Quantity"), validators=[MinValueValidator(1)])
    observation = models.TextField(_("Observation"), blank=True)
    status = models.PositiveSmallIntegerField(
        _("Status"),
        choices=MovementStatusChoices,
        default=MovementStatusChoices.COMPLETED,
    )

    # Stock tracking (readonly)
    previous_stock = models.PositiveIntegerField(_("Previous stock"), editable=False, default=0)
    after_stock = models.PositiveIntegerField(_("After stock"), editable=False, default=0)
    is_increment = models.BooleanField(_("Increment"), editable=False)
    unit_cost_at_movement = models.DecimalField(
        _("Unit cost at movement"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        editable=False,
    )

    # Relationships
    batch = models.ForeignKey("inventory.Batch", on_delete=models.PROTECT, related_name="movements")
    inventory_order = models.ForeignKey(
        "operations.InventoryOrder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movements",
    )

    class Meta:
        db_table = "inventory_movement"
        verbose_name = _("Inventory Movement")
        verbose_name_plural = _("Inventory Movements")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["batch", "-created_at"]),
            models.Index(fields=["movement_type", "status"]),
            models.Index(fields=["inventory_order"]),
        ]
        permissions = (("view_inventorymovements", "Can view movements list"),)

    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.batch} - {self.quantity}"

    def clean(self):
        super().clean()

        if self.movement_type == InventoryMovementType.OUTBOUND:
            if self.quantity > self.batch.current_quantity:
                raise ValidationError(
                    {
                        "quantity": _(
                            f"Insufficient stock. Only {self.batch.current_quantity} available"
                        )
                    }
                )
