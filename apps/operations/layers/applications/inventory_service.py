import logging
from dataclasses import dataclass

from django.db import transaction
from django.db.models import Count
from django.utils.translation import gettext_lazy as _

from apps.inventory.layers.applications import BatchAppService
from apps.inventory.models import Batch, InventoryMovement
from apps.operations.layers.builders import ExitOrderBuilder
from apps.operations.layers.dto import DatatableSearch
from apps.operations.models import ExitDetail, ExitOrder

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
            logger.exception(f"Failed to fetch exit orders: {e}")
            return []

    @staticmethod
    def create_exit_order(payload):
        return (
            ExitOrderBuilder()
            .set_status(payload.status)
            .requested_by(payload.requested_by)
            .set_observations(payload.observations)
            .set_motive(payload.motive)
            .save()
            .build()
        )


@dataclass
class StockAllocation:
    batch: Batch
    quantity: int


class StockAllocator:
    """Allocate stock to batches."""

    @staticmethod
    def allocate(batches: list[Batch], quantity: int) -> list[StockAllocation]:
        allocations = []
        remaining = quantity
        for batch in batches:
            if remaining <= 0:
                break

            taken = min(remaining, batch.current_quantity)
            if taken > 0:
                allocations.append(StockAllocation(batch, taken))
                remaining -= taken

        if remaining > 0:
            raise ValueError(_("Out of stock"))
        return allocations


class InventoryOrchestrator:
    def __init__(self, batch_service=None):
        self.batch_service = batch_service or BatchAppService()

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
    def _consolidate(details_payload: list) -> dict:
        """Consolidate details by supply_id."""
        consolidated = {}
        for item in details_payload:
            consolidated[item.supply_id] = (
                consolidated.get(item.supply_id, 0) + item.quantity_requested
            )
        return consolidated

    @staticmethod
    def _build_detail(order: ExitOrder, alloc: StockAllocation) -> ExitDetail:
        return ExitDetail(
            order=order,
            supply_id=alloc.batch.supply_id,
            batch=alloc.batch,
            quantity_requested=alloc.quantity,
            quantity_dispatched=alloc.quantity,
            unit_cost=alloc.batch.unit_cost,
        )

    @staticmethod
    def _build_movement(
        order: ExitOrder, alloc: StockAllocation, old_stock: int
    ) -> InventoryMovement:
        batch = alloc.batch
        return InventoryMovement(
            batch=batch,
            is_increment=False,
            concept=order.motive,
            quantity=alloc.quantity,
            observation=str(
                _(f"Order dispatch for supply {batch.supply.name} - {batch.supply.code}")
            ),
            previous_stock=old_stock,
            after_stock=int(old_stock - alloc.quantity),
            unit_cost_at_movement=batch.unit_cost,
            movement_type=InventoryMovement.Type.OUTBOUND,
            created_by=order.requested_by,
            exit_order=order,
        )

    @staticmethod
    def _bulk_persist(batches, details, movements):
        Batch.objects.bulk_update(batches, ["current_quantity", "status"])
        ExitDetail.objects.bulk_create(details)
        InventoryMovement.objects.bulk_create(movements)

    @transaction.atomic
    def register_exit(self, order: ExitOrder, details_payload: list):

        batches_to_update, details_to_create, movements_to_create = [], [], []

        for supply_id, quantity in self._consolidate(details_payload).items():
            batches = self.batch_service.retrieve_by_expiry_date(supply_id).select_for_update()
            allocations = StockAllocator.allocate(batches, quantity)

            for alloc in allocations:
                batch = alloc.batch
                old_stock = batch.current_quantity

                batch.current_quantity -= alloc.quantity
                if batch.current_quantity == 0:
                    batch.status = Batch.BatchStatus.DEPLETED

                batches_to_update.append(batch)
                details_to_create.append(self._build_detail(order, alloc))
                movements_to_create.append(self._build_movement(order, alloc, old_stock))

        self._bulk_persist(batches_to_update, details_to_create, movements_to_create)
        order.recalculate_totals()
        order.save()
