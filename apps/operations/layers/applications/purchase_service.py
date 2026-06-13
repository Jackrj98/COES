import logging

from django.db import transaction
from django.db.models import Count
from django.utils.translation import gettext_lazy as _

from apps.inventory.models import Batch, InventoryMovement
from apps.operations.layers.builders import PurchaseOrderBuilder
from apps.operations.layers.dto import DatatableSearch
from apps.operations.models import PurchaseOrder, PurchaseOrderDetail

logger = logging.getLogger(__name__)


class PurchaseAppService:
    @staticmethod
    def retrieve_purchase_orders(params):
        fields = [
            "external_id",
            "order_number",
            "supplier__business_name",
            "supplier__first_name",
            "supplier__last_name",
            "estimated_delivery",
            "actual_delivery",
            "status",
            "created_at",
            "updated_at",
        ]
        try:
            DatatableSearch.retrieve_purchase_orders(params)
            queryset = params.items.annotate(items=Count("details"))
            qs = list(queryset.values(*fields, "items"))
            return params.result(qs)
        except Exception as e:
            logger.exception(f"Failed to fetch purchase orders: {e}")
            return []

    @staticmethod
    def save_purchase_order(payload, instance=None):
        builder = PurchaseOrderBuilder(instance) if instance else PurchaseOrderBuilder()
        try:
            order = (
                builder.set_supplier(payload.supplier_id)
                .set_motive(payload.motive)
                .set_observations(payload.observations)
                .set_estimated_delivery(payload.estimated_delivery)
                .set_actual_delivery(payload.actual_delivery)
                .set_status(payload.status)
            )

            return order.build()
        except ValueError as e:
            logger.error(f"Invalid payload: {e}")
            raise
        except Exception as e:
            logger.exception(f"Failed to create purchase order: {e}")
            raise

    def create_purchase_order(self, payload):
        return self.save_purchase_order(payload)

    def update_purchase_order(self, instance, payload):
        if not instance:
            raise ValueError(_("Purchase order instance is required."))
        return self.save_purchase_order(payload, instance)


class PurchaseOrchestrator:
    @property
    def status_map(self):
        return {
            PurchaseOrder.Status.DRAFT: Batch.BatchStatus.DISCARDED,
            PurchaseOrder.Status.SENT: Batch.BatchStatus.DISCARDED,
            PurchaseOrder.Status.COMPLETED: Batch.BatchStatus.ACTIVE,
            PurchaseOrder.Status.CANCELLED: Batch.BatchStatus.DISCARDED,
        }

    @staticmethod
    def _build_detail(order: PurchaseOrder, detail_data: dict) -> PurchaseOrderDetail:
        return PurchaseOrderDetail(
            order=order,
            supply_id=detail_data["supply_id"],
            batch=detail_data["batch"],
            quantity_requested=detail_data["quantity_requested"],
            quantity_received=detail_data["quantity_received"],
            unit_cost=detail_data["unit_cost"],
            observations=detail_data.get("observations", ""),
        )

    @staticmethod
    def _build_movement(
        order: PurchaseOrder, detail: PurchaseOrderDetail, old_stock: int, incremental=True
    ) -> InventoryMovement:
        prev_stock = old_stock
        after_stock = (
            0 + detail.quantity_received if incremental else old_stock - detail.quantity_received
        )

        if incremental:
            prev_stock = min(old_stock, 0)
            type_mov = InventoryMovement.Type.INBOUND
            observation = f"Purchase Order {order.order_number}"
        else:
            after_stock = 0
            type_mov = InventoryMovement.Type.ADJUSTMENT
            observation = f"Cancellation of Purchase Order {order.order_number}"

        return InventoryMovement(
            batch=detail.batch,
            is_increment=incremental,
            concept=order.motive,
            quantity=detail.quantity_received,
            previous_stock=prev_stock,
            after_stock=after_stock,
            unit_cost_at_movement=detail.unit_cost,
            movement_type=type_mov,
            observation=observation,
            created_by=order.created_by,
            purchase_order=order,
        )

    @staticmethod
    def _apply_batch_updates(details, status: Batch.BatchStatus):
        batches_to_update = []
        for detail in details:
            batch = detail.batch
            batch.status = status
            if status == Batch.BatchStatus.DISCARDED:
                batch.current_quantity = 0
            batches_to_update.append(batch)
        Batch.objects.bulk_update(batches_to_update, ["current_quantity", "status"])

    def _create_movements(self, order, details, incremental=True):

        movements = [
            self._build_movement(order, d, d.quantity_received, incremental) for d in details
        ]
        if movements:
            InventoryMovement.objects.bulk_create(movements)

    @transaction.atomic
    def register_purchase(self, order: PurchaseOrder, details_payload: list):
        batches = [
            Batch(
                batch_number=i["batch_number"],
                supply_id=i["supply_id"],
                expiry_date=i["expiry_date"],
                initial_quantity=i["quantity_received"],
                current_quantity=i["quantity_received"],
                unit_cost=i["unit_cost"],
                status=self.status_map.get(order.status, Batch.BatchStatus.DISCARDED),
            )
            for i in details_payload
        ]
        Batch.objects.bulk_create(batches)

        details = [
            self._build_detail(order, {**item, "batch": batch})
            for item, batch in zip(details_payload, batches)
        ]
        PurchaseOrderDetail.objects.bulk_create(details)

        if order.status == PurchaseOrder.Status.COMPLETED:
            self._create_movements(order, details, incremental=True)
        order.save()

    @transaction.atomic
    def update_purchase_order(self, order: PurchaseOrder, details_payload: list):
        affected = []
        processed_detail_ids = []

        for item in details_payload:
            qty = item["quantity_received"]
            if qty <= 0:
                continue

            batch, _ = Batch.objects.update_or_create(
                supply_id=item["supply_id"],
                batch_number=item["batch_number"],
                defaults={
                    "expiry_date": item["expiry_date"],
                    "initial_quantity": qty,
                    "current_quantity": qty,
                    "unit_cost": item["unit_cost"],
                    "status": self.status_map.get(order.status),
                },
            )

            detail, created = PurchaseOrderDetail.objects.update_or_create(
                order=order,
                supply_id=item["supply_id"],
                batch=batch,
                defaults={
                    "quantity_requested": item["quantity_requested"],
                    "quantity_received": qty,
                    "unit_cost": item["unit_cost"],
                    "observations": item.get("observation", ""),
                },
            )

            processed_detail_ids.append(detail.id)
            affected.append(detail)

        order.details.exclude(id__in=processed_detail_ids).delete()
        # Batch.objects.filter(purchaseorderdetail__isnull=True).delete()
        if order.status == PurchaseOrder.Status.COMPLETED:
            self._create_movements(order, affected, incremental=True)

    @transaction.atomic
    def complete_purchase_order(self, order: PurchaseOrder):
        if order.status == PurchaseOrder.Status.COMPLETED:
            return
        order.status = PurchaseOrder.Status.COMPLETED
        order.save()
        details = order.details.select_related("batch").all()
        self._apply_batch_updates(details, Batch.BatchStatus.ACTIVE)
        self._create_movements(order, details, incremental=True)

    @transaction.atomic
    def cancel_purchase_order(self, order: PurchaseOrder):
        if order.status == PurchaseOrder.Status.CANCELLED:
            return
        order.status = PurchaseOrder.Status.CANCELLED
        order.save()
        details = order.details.select_related("batch").all()
        self._create_movements(order, details, incremental=False)
        self._apply_batch_updates(details, Batch.BatchStatus.DISCARDED)
