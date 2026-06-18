import logging
from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Sum
from django.utils.translation import gettext_lazy as _

from apps.inventory.layers.applications import BatchAppService
from apps.inventory.models import Batch, InventoryMovement
from apps.operations.layers.builders import InventoryOrderBuilder
from apps.operations.layers.dto import DatatableSearch
from apps.operations.models import InventoryOrder, OrderDetail

logger = logging.getLogger(__name__)


@dataclass
class StockAllocation:
    batch: Batch
    quantity: int


class OutboundOrderService:
    REQUIRED_ORDER_FIELDS = ["motive"]

    def __init__(self, batch_service=None):
        self.batch_service = batch_service or BatchAppService()

    @staticmethod
    def get_outbound_orders(params):
        fields = [
            "external_id",
            "motive",
            "order_number",
            "supplier__business_name",
            "supplier__first_name",
            "supplier__last_name",
            "supplier__document_number",
            "scheduled_date",
            "received_date",
            "status",
            "created_at",
            "created_by",
            "updated_at",
            "updated_by",
        ]
        try:
            DatatableSearch.retrieve_outbound_orders(params)
            queryset = params.items.annotate(
                line_items=Count("details"), total=Sum("details__unit_cost")
            )
            qs = list(queryset.values(*fields, "line_items", "total"))
            return params.result(qs)
        except Exception as e:
            logger.exception(f"Failed to fetch outbound orders: {e}")
            return []

    def save_outbound_order(self, instance, payload, line_details, user):
        try:
            with transaction.atomic():
                builder = InventoryOrderBuilder(instance)
                self._build_order_from_payload(builder, payload)
                outbound_order = builder.build()

                self.register_outbound(outbound_order, line_details)
                return outbound_order
        except (ValidationError, ValueError) as e:
            logger.warning(f"Operation aborted: {e}")
            raise
        except Exception:
            logger.exception("Unexpected error in outbound order process")
            raise

    @staticmethod
    def _build_order_from_payload(builder, payload):
        # Validate and set required fields
        for field in ["motive"]:
            value = payload.get(field)
            if not value:
                raise ValidationError({field: f"{field} is required"})

        builder.set_order_type(payload["order_type"])
        builder.set_motive(payload["motive"])
        builder.set_status(InventoryOrder.StatusType.COMPLETED.value)
        # Set optional fields
        if payload.get("observations"):
            builder.set_observations(payload["observations"])

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

    @staticmethod
    def _consolidate(details_payload: list) -> dict:
        """Consolidate details by supply_id."""
        consolidated = {}
        for item in details_payload:
            supply_id = item["supply_id"]
            consolidated[supply_id] = consolidated.get(supply_id, 0) + item["quantity_requested"]

        return consolidated

    @staticmethod
    def _build_detail(order: InventoryOrder, alloc: StockAllocation) -> OrderDetail:
        return OrderDetail(
            inventory_order=order,
            supply_id=alloc.batch.supply_id,
            batch=alloc.batch,
            quantity_requested=alloc.quantity,
            quantity_fulfilled=alloc.quantity,
            unit_cost=alloc.batch.unit_cost,
            observations=order.observations or "",
        )

    @staticmethod
    def _build_movement(order: InventoryOrder, alloc: StockAllocation, old_stock: int):
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
            created_by=order.created_by,
            inventory_order=order,
        )

    @staticmethod
    def _bulk_persist(batches, details, movements):
        Batch.objects.bulk_update(batches, ["current_quantity", "status"])
        OrderDetail.objects.bulk_create(details)
        InventoryMovement.objects.bulk_create(movements)

    def register_outbound(self, order: InventoryOrder, details_payload: list):
        batches_to_update, details_to_create, movements_to_create = [], [], []

        for supply_id, quantity in self._consolidate(details_payload).items():
            batches = self.batch_service.retrieve_by_expiry_date(supply_id).select_for_update()
            allocations = self.allocate(batches, quantity)

            for alloc in allocations:
                batch = alloc.batch
                old_stock = batch.current_quantity

                batch.current_quantity -= alloc.quantity
                if batch.current_quantity <= 0:
                    batch.status = Batch.BatchStatus.DEPLETED

                batches_to_update.append(batch)
                details_to_create.append(self._build_detail(order, alloc))
                movements_to_create.append(self._build_movement(order, alloc, old_stock))

        self._bulk_persist(batches_to_update, details_to_create, movements_to_create)
        order.save()
