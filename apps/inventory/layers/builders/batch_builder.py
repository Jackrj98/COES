from django.utils import timezone

from apps.inventory.models import Batch


class BatchBuilder:
    """Builder for a Batch model."""

    def __init__(self, batch=None):
        self.batch = batch or Batch()

    def set_batch_number(self, batch_number: str) -> "BatchBuilder":
        """Set the batch number with formatting."""
        if batch_number:
            clean_number = "".join(
                c for c in batch_number.strip().upper() if c.isalnum() or c == "-" or c == "_"
            )
            self.batch.batch_number = clean_number
        return self

    def set_expiry_date(self, expiry_date) -> "BatchBuilder":
        """Set the batch expiration date."""
        if expiry_date:
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

    def set_unit_cost(self, cost) -> "BatchBuilder":
        """Set the purchase unit cost with formatting."""
        if cost is not None:
            from decimal import Decimal

            cost_decimal = Decimal(str(cost)) if isinstance(cost, (int, float, str)) else cost
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

    def set_supply(self, supply_id: int) -> "BatchBuilder":
        """Set supply foreign key."""
        if supply_id:
            self.batch.supply_id = supply_id
        return self

    def save(self) -> "BatchBuilder":
        """Save the batch to a database."""
        self.batch.save()
        return self

    def build(self) -> Batch:
        """Build and return a batch instance."""
        return self.batch
