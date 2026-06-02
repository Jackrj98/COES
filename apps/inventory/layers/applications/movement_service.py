import logging

from django.db import transaction
from pydantic import ValidationError

from apps.core.layers import BaseAppService
from apps.inventory.layers.builders import InventoryMovementBuilder
from apps.inventory.layers.dto import DatatableSearch, MovementDTO
from apps.inventory.models import InventoryMovement

logger = logging.getLogger(__name__)


class InventoryMovementAppService(BaseAppService):
    def __init__(self):
        super().__init__(InventoryMovement)

    def get_movements_by_batch(self, batch_external_id: str):
        """Get all movements for a specific batch."""
        try:
            return (
                self.model.active.filter(batch__external_id=batch_external_id)
                .select_related("batch__supply")
                .order_by("-created_at")
            )
        except Exception as e:
            logger.error(f"Error getting movements for batch {batch_external_id}: {e}")
            return self.model.objects.none()

    def get_movements_by_supply(self, supply_external_id: str):
        """Get all movements for all batches of a specific supply."""
        try:
            return (
                self.model.objects.filter(batch__supply__external_id=supply_external_id)
                .select_related("batch", "batch__supply")
                .order_by("-created_at")
            )
        except Exception as e:
            logger.error(f"Error getting movements for supply {supply_external_id}: {e}")
            return self.model.objects.none()

    @staticmethod
    def retrieve_movements(params):
        fields = [
            "external_id",
            "movement_type",
            "concept",
            "quantity",
            "movement_type",
            "previous_stock",
            "after_stock",
            "is_increment",
            "unit_cost_at_movement",
            "status",
            "is_active",
            "created_at",
            "updated_at",
            "batch__number",
            "batch__supply__name",
            "batch__supply__code",
        ]
        try:
            DatatableSearch.retrieve_inventory_movements(params)
            queryset = params.items
            qs = list(queryset.values(*fields))
            return params.result(qs)
        except Exception as e:
            logger.exception(f"Failed to fetch inventory movements: {e}")
            return params.result([]) if hasattr(params, "result") else []

    @transaction.atomic
    def register_movement(self, payload: dict) -> InventoryMovement:
        try:
            dto = MovementDTO(**payload)
            # Build the inventory movement
            builder = InventoryMovementBuilder()
            movement = (
                builder.set_batch(dto.batch_id)
                .set_type(dto.movement_type)
                .set_concept(dto.concept)
                .set_quantity(dto.quantity)
                .set_observation(dto.observation)
                .set_stock_data(dto.previous_stock, dto.after_stock)
                .set_unit_cost(dto.unit_cost_at_movement)
                .set_status(dto.status)
                .save()
                .build()
            )

            return movement

        except ValidationError as e:
            logger.warning(f"Validation error: {e.json()}")
            raise
        except Exception as e:
            logger.error(f"Error saving inventory movement: {e}", exc_info=True)

            raise

    @transaction.atomic
    def cancel_movement(self, movement_id: int, reason: str):
        """Undo a transaction by creating an offsetting entry."""
        try:
            # 1. Recovery original movement
            original = self.model.objects.get(id=movement_id)
            original.status = InventoryMovement.Status.CANCELLED
            original.save()

            builder = InventoryMovementBuilder()
            reversal = (
                builder.set_batch(original.batch)
                .set_type(InventoryMovement.Type.ADJUSTMENT)
                .set_status(InventoryMovement.Status.COMPLETED)
                .set_concept(f"_('Reversal of movement') #{original.id}")
                .set_quantity(original.quantity)
                .set_observation(f"_('Voided'): {reason}")
                .set_stock_data(previous=original.after_stock, after=original.previous_stock)
                .set_unit_cost(original.unit_cost_at_movement)
                .save()
                .build()
            )

            return reversal

        except ValidationError as e:
            logger.warning(f"Validation error: {e.json()}")
            raise
        except Exception as e:
            logger.error(f"Error saving inventory movement: {e}", exc_info=True)
            raise
