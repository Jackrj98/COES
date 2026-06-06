import logging

from django.db import transaction
from django.db.models import Count
from django.utils.translation import gettext_lazy as _

from apps.inventory.layers.applications import BatchAppService, InventoryMovementAppService
from apps.operations.layers.builders import ExitDetailBuilder, ExitOrderBuilder
from apps.operations.layers.dto import DatatableSearch

logger = logging.getLogger(__name__)


class OrderAppService:
    @staticmethod
    def retrieve_exit_orders(params):
        fields = [
            "external_id",
            "order_number",
            "motive",
            "requested_by",
            "subtotal",
            "total",
            "status",
            "created_at",
            "updated_at",
        ]
        try:
            DatatableSearch.retrieve_exit_orders(params)
            queryset = params.items.annotate(items=Count("details"))
            qs = list(queryset.values(*fields, "items"))
            return params.result(qs)
        except Exception as e:
            logger.exception(f"Failed to fetch suppliers: {e}")
            return []

    @classmethod
    @transaction.atomic
    def register_exit_order(cls, payload):
        order = cls._create_order(payload)
        batch_service = BatchAppService()

        consolidated_details = {}
        for item in payload.details:
            supply_id = item.supply_id
            qty = item.quantity_requested
            consolidated_details[supply_id] = consolidated_details.get(supply_id, 0) + qty

        for supply_id, total_requested in consolidated_details.items():
            remaining_to_dispatch = total_requested

            available_batches = batch_service.retrieve_by_expiry_date(supply_id).select_for_update()
            if not available_batches:
                raise ValueError(_(f"There is no stock available for supply {supply_id}."))

            remaining_to_dispatch = cls._update_bath(
                order, available_batches, remaining_to_dispatch
            )

            if remaining_to_dispatch > 0:
                raise ValueError(
                    _(
                        f"Insufficient stock for supply {supply_id}. {remaining_to_dispatch} items are out of stock."
                    )
                )

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
