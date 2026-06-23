from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.inventory.models import Batch


class BatchBuilder:
    """Builder for a Batch model."""

    def __init__(self, batch=None):
        self.batch = batch or Batch()

    def set_batch_number(self, batch_number: str) -> "BatchBuilder":
        """Set the batch number with formatting."""
        if not batch_number or str(batch_number).strip() == "":
            raise ValidationError({"batch_number": [_("This field cannot be empty.")]})

        clean_number = "".join(
            c for c in batch_number.strip().upper() if c.isalnum() or c == "-" or c == "_"
        )
        self.batch.batch_number = clean_number
        return self

    def set_manufacture_date(self, manufacture_date):
        if manufacture_date:
            self.batch.manufacture_date = manufacture_date
        return self

    def set_expiry_date(self, expiry_date) -> "BatchBuilder":
        """Set the batch expiration date."""
        if not expiry_date or str(expiry_date).strip() == "":
            raise ValidationError({"expiry_date": [_("This field cannot be empty.")]})

        if isinstance(expiry_date, str):
            from datetime import datetime

            expiry_date = datetime.strptime(expiry_date, "%Y-%m-%d").date()
        self.batch.expiry_date = expiry_date
        return self

    def set_initial_quantity(self, initial_quantity: int) -> "BatchBuilder":
        """Set batch stock (must be non-negative)."""
        if initial_quantity is not None:
            self.batch.initial_quantity = max(0, initial_quantity)
        return self

    def set_current_quantity(self, current_quantity: int) -> "BatchBuilder":
        """Set the current available quantity."""
        if current_quantity is not None:
            self.batch.current_quantity = current_quantity
        return self

    def set_unit_cost(self, unit_cost) -> "BatchBuilder":
        """Set the purchase unit cost with formatting."""
        if not unit_cost or float(unit_cost) == 0:
            raise ValidationError({"unit_cost": [_("This field cannot be zero or negative.")]})

        if unit_cost is not None:
            from decimal import Decimal

            cost_decimal = (
                Decimal(str(unit_cost)) if isinstance(unit_cost, (int, float, str)) else unit_cost
            )
            self.batch.unit_cost = max(Decimal("0.00"), cost_decimal)
        return self

    def set_is_active(self, is_active: bool = True) -> "BatchBuilder":
        """Set the batch active status."""
        self.batch.is_active = is_active
        return self

    def set_status(self, status: int) -> "BatchBuilder":
        """Set batch status with validation."""
        if status is not None:
            if status in Batch.BatchStatus:
                self.batch.status = status
            if self.batch.expiry_date < timezone.now().date():
                self.batch.status = Batch.BatchStatus.EXPIRED.value
        return self

    def set_status_by_expiration(self, force=False) -> "BatchBuilder":
        batch_status = Batch.BatchStatus
        if force or self.batch.status == batch_status.DISCARDED:
            if self.batch.expiry_date:
                today = timezone.now().date()
                if self.batch.expiry_date < today:
                    self.batch.status = batch_status.EXPIRED
                elif self.batch.status != batch_status.EXPIRED:
                    self.batch.status = batch_status.ACTIVE
        return self

    def set_notes(self, notes: str) -> "BatchBuilder":
        """Set batch notes."""
        if notes:
            self.batch.notes = notes.strip()[:500]
        return self

    def set_supply(self, supply_id: int) -> "BatchBuilder":
        """Set supply foreign key."""
        if not supply_id:
            raise ValidationError({"supply": [_("This field cannot be empty.")]})

        if supply_id:
            self.batch.supply_id = supply_id
        return self

    def set_supplier(self, supplier_id: int) -> "BatchBuilder":
        if supplier_id:
            self.batch.supplier_id = supplier_id
        return self

    def build(self) -> Batch:
        """Build and return a batch instance."""
       # self.batch.full_clean()
        self.batch.save()
        return self.batch
