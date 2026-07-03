import logging

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from apps.inventory.layers.applications import BatchAppService, InventoryMovementAppService
from apps.inventory.models import Batch, InventoryMovement
from apps.operations.layers.builders import InventoryOrderBuilder, OrderDetailBuilder
from apps.operations.layers.dto import DatatableSearch
from apps.operations.models import InboundOrder

logger = logging.getLogger(__name__)


class InboundOrderService:
    REQUIRED_ORDER_FIELDS = ["motive", "supplier", "scheduled_date"]
    STATUSES = {
        InboundOrder.StatusType.COMPLETED: Batch.BatchStatus.ACTIVE,
    }

    @staticmethod
    def get_inbound_orders(params):
        fields = [
            "external_id",
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
            DatatableSearch.retrieve_orders(params)
            queryset = params.items.annotate(line_items=Count("details"))
            qs = list(queryset.values(*fields, "line_items"))
            return params.result(qs)
        except Exception as e:
            logger.exception(f"Failed to fetch inbound orders: {e}")
            return []

    def save_inbound_order(self, instance, payload, line_details, user):
        try:
            builder = InventoryOrderBuilder(instance)

            self._build_order_from_payload(builder, payload)
            inbound_order = builder.build()

            detail_builder = OrderDetailBuilder(order=inbound_order)
            self._process_line_details(detail_builder, line_details, inbound_order)
            return inbound_order

        except ValidationError as e:
            logger.error(f"Validation error in inbound order: {e}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error creating inbound order: {e}")
            raise

    def _build_order_from_payload(self, builder, payload):
        # Validate and set required fields
        for field in self.REQUIRED_ORDER_FIELDS:
            value = payload.get(field)
            if not value:
                raise ValidationError({field: f"{field} is required"})

        builder.set_order_type(payload["order_type"])
        builder.set_motive(payload["motive"])
        builder.set_status(payload["status"])
        builder.set_supplier(payload["supplier"])
        builder.set_scheduled_date(payload["scheduled_date"])

        # Set optional fields
        if payload.get("observations"):
            builder.set_observations(payload["observations"])

        if payload.get("received_date"):
            builder.set_received_date(payload["received_date"])

    def _process_line_details(self, builder, line_details, inbound_order):
        if not line_details:
            raise ValidationError({"line_details": "At least one line detail is required"})

        for line in line_details:
            self._validate_line_detail(line)

            # Create batch
            batch = self._build_batch(line, inbound_order)

            line["batch"] = batch
            self._build_line_detail(builder, line)
        builder.save()

    @staticmethod
    def _validate_line_detail(line):
        required_fields = ["supply_id", "quantity_requested"]
        missing_fields = [field for field in required_fields if field not in line]

        if missing_fields:
            raise ValidationError(
                {"line_details": f"Missing required fields: {', '.join(missing_fields)}"}
            )

    @staticmethod
    def _build_line_detail(builder, line):
        (
            builder.start_line(supply_id=line["supply_id"])
            .set_unit_cost(line.get("unit_cost"))
            .set_requested_quantity(line["quantity_requested"])
            .set_fulfilled_quantity(line.get("quantity_fulfilled", 0))
            .set_batch(line["batch"])
            .set_observations(line.get("observations"))
            .finish_line()
        )

    @staticmethod
    def _build_batch(payload, inbound_order):
        return BatchAppService().register_batch(
            payload={
                "batch_number": payload["batch_number"],
                "expiry_date": payload["expiry_date"],
                "unit_cost": payload["unit_cost"],
                "initial_quantity": payload["quantity_requested"],
                "current_quantity": payload["quantity_requested"],
                "status": 0,
                "notes": _(f"Batch created from inbound order {inbound_order.order_number}"),
                "is_active": False,
                "supply_id": payload["supply_id"],
                "supplier_id": inbound_order.supplier.id,
            }
        )

    @staticmethod
    def _build_movement(batch, order_id, movement_type, created_by, concept=None, quantity=None):
        qty = quantity if quantity is not None else batch.current_quantity

        InventoryMovementAppService().register_movement(
            payload={
                "order_id": order_id,
                "batch_id": batch.id,
                "movement_type": movement_type,
                "concept": concept or str(_("Inventory operation")),
                "quantity": qty,
                "observation": str(
                    _("Movement for batch {batch_number}").format(batch_number=batch.batch_number)
                ),
                "previous_stock": 0,
                "after_stock": batch.current_quantity,
                "unit_cost_at_movement": batch.unit_cost,
                "status": InventoryMovement.MovementStatusChoices.COMPLETED,
                "created_by": created_by,
            }
        )

    @staticmethod
    def _build_movements(batch, created_by):
        InventoryMovementAppService().register_movement(
            payload={
                "batch_id": batch.id,
                "movement_type": InventoryMovement.Type.INBOUND,
                "concept": str(_("Initial stock entry")),
                "quantity": batch.initial_quantity,
                "observation": str(
                    _("Batch creation with initial quantity: {quantity}").format(
                        quantity=batch.initial_quantity
                    )
                ),
                "previous_stock": 0,
                "after_stock": batch.initial_quantity,
                "unit_cost_at_movement": batch.unit_cost,
                "status": InventoryMovement.MovementStatusChoices.COMPLETED,
                "created_by": created_by or "system",
            }
        )

    @transaction.atomic
    def update_inbound_order(self, inventory_order, payload, details_payload):
        processed_detail_ids = []
        inventory_order.status = payload["status"]
        inventory_order.received_date = payload.get("received_date") or now().date()
        inventory_order.save()

        for detail in details_payload:
            qty = detail.get("quantity_fulfilled", 0)
            if qty <= 0:
                continue

            # 1. Update/Create Batch
            batch = self._get_or_create_batch(inventory_order, detail, qty)
            if inventory_order.status == InboundOrder.StatusType.COMPLETED:
                self._build_movement(
                    batch=batch,
                    order_id=inventory_order.id,
                    movement_type=InventoryMovement.Type.INBOUND,
                    concept=_("Initial stock entry"),
                    quantity=qty,
                    created_by=inventory_order.created_by,
                )
            # 2. Update/Create OrderDetail
            order_detail, create = inventory_order.details.update_or_create(
                supply_id=detail["supply_id"],
                batch=batch,
                defaults={
                    "quantity_requested": detail["quantity_requested"],
                    "quantity_fulfilled": qty,
                    "unit_cost": detail["unit_cost"],
                    "observations": detail.get("observations", ""),
                    "is_active": True,
                    "status": Batch.BatchStatus.ACTIVE,
                },
            )
            processed_detail_ids.append(order_detail.id)

        # 3. Delete details no longer present in the payload
        inventory_order.details.exclude(id__in=processed_detail_ids).delete()
        return inventory_order

    def _get_or_create_batch(self, order, detail, qty):
        batch, create = Batch.objects.update_or_create(
            supply_id=detail["supply_id"],
            batch_number=detail["batch_number"],
            defaults={
                "expiry_date": detail["expiry_date"],
                "initial_quantity": qty,
                "current_quantity": qty,
                "unit_cost": detail["unit_cost"],
                "status": self.STATUSES.get(order.status, Batch.BatchStatus.DISCARDED),
                "is_active": True,
                "notes": _(f"Batch updated from inbound order {order.order_number}"),
                "supplier_id": order.supplier.id,
            },
        )
        return batch

    @transaction.atomic
    def complete_purchase_order(self, inventory_order):
        state_complete = InboundOrder.StatusType.COMPLETED
        if inventory_order.status == state_complete:
            return inventory_order

        inventory_order.status = state_complete
        inventory_order.received_date = now().date()
        inventory_order.save()
        details = inventory_order.details.select_related("batch").all()

        for detail in details:
            detail.quantity_fulfilled = detail.quantity_requested
            detail.batch.current_quantity = detail.quantity_fulfilled
            detail.batch.status = Batch.BatchStatus.ACTIVE
            detail.is_active = True
            detail.batch.save()
            detail.save()
            batch = detail.batch
            self._build_movement(
                batch,
                order_id=inventory_order.id,
                movement_type=InventoryMovement.Type.INBOUND,
                concept=str(_("Initial stock entry")),
                quantity=batch.current_quantity,
                created_by=inventory_order.created_by,
            )
        return inventory_order

    @transaction.atomic
    def cancel_purchase_order(self, order: InboundOrder):
        if order.status == InboundOrder.StatusType.CANCELLED:
            return order

        details = order.details.select_related("batch").all()

        batches_to_update = []
        for detail in details:
            batch = detail.batch
            if batch:
                batch.current_quantity = 0
                batch.status = Batch.BatchStatus.DISCARDED
                batches_to_update.append(batch)

        if batches_to_update:
            Batch.objects.bulk_update(batches_to_update, ["current_quantity", "status"])

        order.status = InboundOrder.StatusType.CANCELLED
        order.save()
        return order
