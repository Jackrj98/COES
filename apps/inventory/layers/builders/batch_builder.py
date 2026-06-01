from django.utils import timezone

from apps.inventory.models import Batch


class BatchBuilder:
    """Builder for a Batch model."""

    def __init__(self, batch=None):
        self.batch = batch or Batch()

    def set_number(self, number: str) -> "BatchBuilder":
        """Set the batch number with formatting."""
        if number:
            clean_number = "".join(
                c for c in number.strip().upper() if c.isalnum() or c == "-" or c == "_"
            )
            self.batch.number = clean_number
        return self

    def set_due_date(self, due_date) -> "BatchBuilder":
        """Set the batch expiration date."""
        if due_date:
            if isinstance(due_date, str):
                from datetime import datetime

                due_date = datetime.strptime(due_date, "%Y-%m-%d").date()
            self.batch.due_date = due_date
        return self

    def set_stock(self, stock: int) -> "BatchBuilder":
        """Set batch stock (must be non-negative)."""
        if stock is not None:
            self.batch.stock = max(0, stock)
        return self

    def set_purchase_unit_cost(self, cost) -> "BatchBuilder":
        """Set the purchase unit cost with formatting."""
        if cost is not None:
            from decimal import Decimal

            cost_decimal = Decimal(str(cost)) if isinstance(cost, (int, float, str)) else cost
            self.batch.purchase_unit_cost = max(Decimal("0.00"), cost_decimal)
        return self

    def set_status(self, status: int) -> "BatchBuilder":
        """Set batch status with validation."""
        if status is not None:
            valid_statuses = [choice[0] for choice in Batch.Status.choices]
            if status in valid_statuses:
                self.batch.status = status
        return self

    def set_supply(self, supply_id: int) -> "BatchBuilder":
        """Set supply foreign key."""
        if supply_id:
            self.batch.supply_id = supply_id
        return self

    def set_purchase_order(self, purchase_order_id: int | None) -> "BatchBuilder":
        """Set purchase order foreign key."""
        if purchase_order_id:
            self.batch.purchase_order_id = purchase_order_id
        return self

    def set_is_active(self, is_active: bool = True) -> "BatchBuilder":
        """Set the batch active status."""
        self.batch.is_active = is_active
        return self

    def set_status_by_expiration(self) -> "BatchBuilder":
        """Automatically set status based on expiration date."""
        if self.batch.due_date:
            today = timezone.now().date()
            if self.batch.due_date < today:
                self.batch.status = Batch.Status.EXPIRED
            elif self.batch.status != Batch.Status.DISCARDED:
                self.batch.status = Batch.Status.ACTIVE
        return self

    def save(self) -> "BatchBuilder":
        """Save the batch to a database."""
        self.batch.save()
        return self

    def build(self) -> Batch:
        """Build and return a batch instance."""
        return self.batch
