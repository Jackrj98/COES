import logging

from django.db import transaction
from django.db.models import Count
from django.utils.translation import gettext_lazy as _

from apps.inventory.layers.applications import BatchAppService, InventoryMovementAppService
from apps.operations.layers.builders import ExitDetailBuilder, ExitOrderBuilder
from apps.operations.layers.dto import DatatableSearch

from apps.inventory.models import Batch, InventoryMovement
from apps.operations.models import ExitDetail, ExitOrder
logger = logging.getLogger(__name__)


class InventoryService:

    @classmethod
    @transaction.atomic
    def register_exit_order(cls, payload):
        order = cls._create_order(payload)
        batch_service = BatchAppService()

        # list of batches to update
        batches_to_update = []
        details_to_create = []
        movements_to_create = []

        consolidated = {}
        for item in payload.details:
            consolidated[item.supply_id] = consolidated.get(item.supply_id, 0) + item.quantity_requested

        for supply_id, total_requested in consolidated.items():
            # Atomic batch lock for this input
            available_batches = batch_service.retrieve_by_expiry_date(supply_id).select_for_update()

            if not available_batches.exists():
                raise ValueError(_(f"No stock for supply {supply_id}."))

            remaining = total_requested
            for batch in available_batches:
                if remaining <= 0:
                    break

                taken = min(remaining, batch.current_quantity)
                if taken <= 0: 
                    continue

                # Prepare Batch Update
                batch.current_quantity -= taken
                if batch.current_quantity == 0:
                    batch.status = Batch.BatchStatus.DEPLETED
                batches_to_update.append(batch)

                # 2. Preparar Detalle y Movimiento (instancias, no .save())
                details_to_create.append(ExitDetail(order=order, supply_id=batch.supply_id, batch=batch, quantity_requested=taken, unit_cost=batch.unit_cost))
                movements_to_create.append(InventoryMovement(batch=batch, concept=order.motive, quantity=taken, ...)) # Ajusta campos

                remaining -= taken

            if remaining > 0:
                raise ValueError(_(f"Insufficient stock for {supply_id}."))

        # 3. Persistencia Unificada (Bulk Operations)
        Batch.objects.bulk_update(batches_to_update, ['current_quantity', 'status'])
        ExitDetail.objects.bulk_create(details_to_create)
        InventoryMovement.objects.bulk_create(movements_to_create)

        order.recalculate_totals()
        order.save()
        return order

    @staticmethod
    def _create_order(payload):
        return (
            ExitOrderBuilder()
            .set_status(payload.status)
            .requested_by(payload.requested_by)
            .set_observations(payload.observations)
            .set_motive(payload.motive)
            .save()
            .build()
        )

    @staticmethod
    def _register_details(order_id, batch, quantity):
        (
            ExitDetailBuilder()
            .set_order(order_id)
            .set_supply(batch.supply_id)
            .set_batch(batch.id)
            .set_quantity_requested(quantity)
            .set_unit_cost(batch.unit_cost)
            .save()
            .build()
        )

    @staticmethod
    def _register_outbound_movement(order, batch, quantity):
        supply = batch.supply
        movement_service = InventoryMovementAppService()
        movement_payload = {
            "batch_id": batch.id,
            "concept": order.motive,
            "quantity": quantity,
            "observation": str(_(f"Order dispatch for supply {supply.name} - {supply.code}")),
            "previous_stock": batch.current_quantity,
            "after_stock": batch.current_quantity - quantity,
            "unit_cost_at_movement": batch.unit_cost,
        }
        movement_service.register_outbound(payload=movement_payload)

    @classmethod
    def _update_bath(cls, order, available_batches, remaining_to_dispatch):

        for batch in available_batches:
            if remaining_to_dispatch <= 0:
                break

            taken_from_this_batch = min(remaining_to_dispatch, batch.current_quantity)

            cls._register_details(order.id, batch, taken_from_this_batch)
            cls._register_outbound_movement(order, batch, taken_from_this_batch)

            batch.current_quantity -= taken_from_this_batch
            batch.save()

            remaining_to_dispatch -= taken_from_this_batch

        return remaining_to_dispatch