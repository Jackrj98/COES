import logging

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.inventory.layers.applications import BatchAppService, InventoryMovementAppService

logger = logging.getLogger(__name__)


class InventoryAppService:
    @transaction.atomic
    def processed_out(self, supply_id: int, quantity: int, payload: dict):

        movements = []
        balance = quantity
        batch_service = BatchAppService()

        # Retrieve batches ordered by due date and lock rows to prevent concurrency issues
        batches = batch_service.retrieve_by_due_date(supply_id).select_for_update()

        # Validate total stock availability before processing any batch
        total_available = sum(b.stock for b in batches)
        if total_available < quantity:
            raise ValueError(
                _("Insufficient stock. Available: %(total)s, Requested: %(req)s")
                % {"total": total_available, "req": quantity}
            )

        # Iterate through batches and deduct quantities
        for batch in batches:
            if balance <= 0:
                break

            # Determine the amount to subtract from the current batch
            quantity_out = min(batch.stock, balance)

            # Prepare movement data ensuring defaults if values are missing in payload
            movement_data = {
                "batch_id": batch.id,
                "quantity": quantity_out,
                "previous_stock": batch.stock,
                "unit_cost_at_movement": batch.purchase_unit_cost,
                "concept": payload.get("concept", "Sale"),
                "observation": payload.get("observation", ""),
                "movement_date": payload.get("movement_date", timezone.localdate()),
            }

            # Register the outbound movement
            movement = InventoryMovementAppService().register_outbound(payload=movement_data)
            movements.append(movement)

            # Update the specific batch stock level
            batch_service.update_batch_stock(instance=batch, quantity=batch.stock - quantity_out)

            # Deduct from the remaining balance to be processed
            balance -= quantity_out

        return movements

    @transaction.atomic
    def register_outbound(self, supply_ref: str, quantity: int):

        try:
            stock_total = BatchAppService().retrieve_stock_total(supply_ref)
            if quantity > stock_total:
                raise ValueError("Stock insufficient")
            return 0
        except Exception as e:
            logger.error(f"Error saving inventory movement: {e}", exc_info=True)
            raise
