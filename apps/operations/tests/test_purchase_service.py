# apps/operations/tests/test_purchase_service.py

import datetime
from decimal import Decimal

import pytest
from django.test import RequestFactory
from django.utils import timezone

from apps.core.layers.dto import DataTableParams
from apps.inventory.models import Batch, InventoryMovement, Supply
from apps.operations.layers.applications import PurchaseAppService, PurchaseOrchestrator
from apps.operations.layers.dto import PurchaseOrderDetailDTO, PurchaseOrderDTO
from apps.operations.models import PurchaseOrder, PurchaseOrderDetail

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def supply(db):
    return Supply.objects.create(name="Test Supply", code="SUP001", description="Test Description")


@pytest.fixture
def supplier(db):
    from apps.operations.models import Supplier

    return Supplier.objects.create(
        business_name="Test Supplier",
        first_name="Contact Person",
        last_name="Contact Person",
        document_number="2222222222",
        email="supplier@test.com",
        phone="123456789",
    )


@pytest.fixture
def purchase_order_dto(supplier, supply):
    return PurchaseOrderDTO(
        supplier_id=supplier.id,
        motive="Test purchase",
        observations="Test observations",
        estimated_delivery=timezone.now().date() + datetime.timedelta(days=7),
        actual_delivery=timezone.now().date() + datetime.timedelta(days=14),
        status=PurchaseOrder.Status.DRAFT,
        details=[
            PurchaseOrderDetailDTO(
                supply_id=supply.id,
                quantity_requested=100,
                quantity_received=0,
                unit_cost=Decimal("50.00"),
            )
        ],
    )


@pytest.fixture
def purchase_order(supplier):
    return PurchaseOrder.objects.create(
        order_number="PO-001",
        supplier=supplier,
        motive="Test purchase",
        observations="Test observations",
        estimated_delivery=timezone.now().date() + datetime.timedelta(days=7),
        status=PurchaseOrder.Status.DRAFT,
    )


@pytest.fixture
def orchestrator():
    return PurchaseOrchestrator()


# ---------------------------------------------------------------------------
# Test PurchaseAppService
# ---------------------------------------------------------------------------


class TestPurchaseAppService:
    @pytest.mark.django_db
    def test_create_purchase_order_success(self, purchase_order_dto):
        order = PurchaseAppService().create_purchase_order(purchase_order_dto)

        assert order.id is not None
        assert order.supplier_id == purchase_order_dto.supplier_id
        assert order.motive == "Test purchase"
        assert order.status == PurchaseOrder.Status.DRAFT

    @pytest.mark.django_db
    def test_create_purchase_order_without_supplier_raises_error(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PurchaseOrderDTO(
                supplier_id=None,
                motive="Test",
                observations="Test",
                estimated_delivery=None,
                actual_delivery=None,
                status=PurchaseOrder.Status.DRAFT,
                details=[],
            )

    @pytest.mark.django_db
    def test_update_purchase_order_success(self, purchase_order, purchase_order_dto):
        service = PurchaseAppService()

        updated = service.update_purchase_order(purchase_order, purchase_order_dto)

        assert updated.id == purchase_order.id
        assert updated.motive == purchase_order_dto.motive

    @pytest.mark.django_db
    def test_update_purchase_order_without_instance_raises_error(self, purchase_order_dto):
        service = PurchaseAppService()

        with pytest.raises(ValueError, match="Purchase order instance is required"):
            service.update_purchase_order(None, purchase_order_dto)

    @pytest.mark.django_db
    def test_retrieve_purchase_orders_empty(self):

        factory = RequestFactory()
        request = factory.get(
            "/api/purchase-orders/",
            {"draw": "1", "start": "0", "length": "10", "search[value]": ""},
        )

        params = DataTableParams(request, **dict(request.GET.lists()))
        result = PurchaseAppService.retrieve_purchase_orders(params)

        assert result["data"] == []
        assert result["recordsTotal"] == 0

    @pytest.mark.django_db
    def test_retrieve_purchase_orders_with_data(self, purchase_order):
        factory = RequestFactory()
        request = factory.get(
            "/api/purchase-orders/",
            {"draw": "1", "start": "0", "length": "10", "search[value]": ""},
        )

        params = DataTableParams(request, **dict(request.GET.lists()))
        result = PurchaseAppService.retrieve_purchase_orders(params)

        assert result["data"] is not None
        assert len(result["data"]) >= 1


# ---------------------------------------------------------------------------
# Test PurchaseOrchestrator - Register Purchase
# ---------------------------------------------------------------------------


class TestPurchaseOrchestratorRegister:
    @pytest.mark.django_db
    def test_register_purchase_success(self, orchestrator, supplier, supply):

        order = PurchaseOrder.objects.create(
            order_number="PO-REG-001",
            supplier=supplier,
            motive="Test purchase",
            status=PurchaseOrder.Status.COMPLETED,
        )

        details_payload = [
            {
                "supply_id": supply.id,
                "batch_number": "BATCH-REG-001",
                "expiry_date": timezone.now().date() + datetime.timedelta(days=365),
                "quantity_requested": 100,
                "quantity_received": 100,
                "unit_cost": Decimal("50.00"),
                "observation": "Test",
            }
        ]

        orchestrator.register_purchase(order, details_payload)
        batch = Batch.objects.get(batch_number="BATCH-REG-001")
        assert batch.current_quantity == 100
        assert batch.status == Batch.BatchStatus.ACTIVE

        detail = PurchaseOrderDetail.objects.get(order=order)
        assert detail.quantity_received == 100

        movement = InventoryMovement.objects.get(purchase_order=order)
        assert movement.is_increment is True
        assert movement.quantity == 100

    @pytest.mark.django_db
    def test_register_purchase_with_draft_status(self, orchestrator, supplier, supply):
        order = PurchaseOrder.objects.create(
            order_number="PO-REG-002",
            supplier=supplier,
            motive="Test purchase",
            status=PurchaseOrder.Status.DRAFT,
        )

        details_payload = [
            {
                "supply_id": supply.id,
                "batch_number": "BATCH-REG-002",
                "expiry_date": timezone.now().date() + datetime.timedelta(days=365),
                "quantity_requested": 100,
                "quantity_received": 100,
                "unit_cost": Decimal("50.00"),
                "observation": "Test",
            }
        ]

        orchestrator.register_purchase(order, details_payload)

        batch = Batch.objects.get(batch_number="BATCH-REG-002")
        assert batch.current_quantity == 100
        assert batch.status == Batch.BatchStatus.DISCARDED

        movements = InventoryMovement.objects.filter(purchase_order=order)
        assert movements.count() == 0

    @pytest.mark.django_db
    def test_register_purchase_multiple_batches(self, orchestrator, supplier, supply):

        order = PurchaseOrder.objects.create(
            order_number="PO-REG-003",
            supplier=supplier,
            motive="Test purchase",
            status=PurchaseOrder.Status.COMPLETED,
        )

        details_payload = [
            {
                "supply_id": supply.id,
                "batch_number": "BATCH-MULTI-001",
                "expiry_date": timezone.now().date() + datetime.timedelta(days=365),
                "quantity_requested": 100,
                "quantity_received": 100,
                "unit_cost": Decimal("50.00"),
                "observation": "Batch 1",
            },
            {
                "supply_id": supply.id,
                "batch_number": "BATCH-MULTI-002",
                "expiry_date": timezone.now().date() + datetime.timedelta(days=180),
                "quantity_requested": 50,
                "quantity_received": 50,
                "unit_cost": Decimal("45.00"),
                "observation": "Batch 2",
            },
        ]

        orchestrator.register_purchase(order, details_payload)

        batches = Batch.objects.filter(batch_number__startswith="BATCH-MULTI")
        assert batches.count() == 2

        details = PurchaseOrderDetail.objects.filter(order=order)
        assert details.count() == 2

        movements = InventoryMovement.objects.filter(purchase_order=order)
        assert movements.count() == 2


# ---------------------------------------------------------------------------
# Test PurchaseOrchestrator - Update Purchase
# ---------------------------------------------------------------------------


class TestPurchaseOrchestratorUpdate:
    @pytest.mark.django_db
    def test_update_purchase_order_add_batch(self, orchestrator, purchase_order, supply):

        initial_payload = [
            {
                "supply_id": supply.id,
                "batch_number": "BATCH-UPD-001",
                "expiry_date": timezone.now().date() + datetime.timedelta(days=365),
                "quantity_requested": 100,
                "quantity_received": 100,
                "unit_cost": Decimal("50.00"),
                "observation": "Initial",
            }
        ]
        orchestrator.register_purchase(purchase_order, initial_payload)

        update_payload = [
            {
                "supply_id": supply.id,
                "batch_number": "BATCH-UPD-001",
                "expiry_date": timezone.now().date() + datetime.timedelta(days=365),
                "quantity_requested": 100,
                "quantity_received": 100,
                "unit_cost": Decimal("50.00"),
                "observation": "Updated",
            },
            {
                "supply_id": supply.id,
                "batch_number": "BATCH-UPD-002",
                "expiry_date": timezone.now().date() + datetime.timedelta(days=180),
                "quantity_requested": 50,
                "quantity_received": 50,
                "unit_cost": Decimal("45.00"),
                "observation": "New",
            },
        ]

        purchase_order.status = PurchaseOrder.Status.COMPLETED
        purchase_order.save()

        orchestrator.update_purchase_order(purchase_order, update_payload)

        batches = Batch.objects.filter(batch_number__startswith="BATCH-UPD")
        assert batches.count() == 2

        details = PurchaseOrderDetail.objects.filter(order=purchase_order)
        assert details.count() == 2

    @pytest.mark.django_db
    def test_update_purchase_order_remove_batch(self, orchestrator, purchase_order, supply):

        initial_payload = [
            {
                "supply_id": supply.id,
                "batch_number": "BATCH-REM-001",
                "expiry_date": timezone.now().date() + datetime.timedelta(days=365),
                "quantity_requested": 100,
                "quantity_received": 100,
                "unit_cost": Decimal("50.00"),
                "observation": "Batch 1",
            },
            {
                "supply_id": supply.id,
                "batch_number": "BATCH-REM-002",
                "expiry_date": timezone.now().date() + datetime.timedelta(days=180),
                "quantity_requested": 50,
                "quantity_received": 50,
                "unit_cost": Decimal("45.00"),
                "observation": "Batch 2",
            },
        ]
        orchestrator.register_purchase(purchase_order, initial_payload)

        update_payload = [
            {
                "supply_id": supply.id,
                "batch_number": "BATCH-REM-001",
                "expiry_date": timezone.now().date() + datetime.timedelta(days=365),
                "quantity_requested": 100,
                "quantity_received": 100,
                "unit_cost": Decimal("50.00"),
                "observation": "Only batch",
            }
        ]

        orchestrator.update_purchase_order(purchase_order, update_payload)

        details = PurchaseOrderDetail.objects.filter(order=purchase_order)
        assert details.count() == 1
        assert details.first().batch.batch_number == "BATCH-REM-001"


# ---------------------------------------------------------------------------
# Test PurchaseOrchestrator - Complete Purchase
# ---------------------------------------------------------------------------


class TestPurchaseOrchestratorComplete:
    @pytest.mark.django_db
    def test_complete_purchase_order_success(self, orchestrator, purchase_order, supply):

        details_payload = [
            {
                "supply_id": supply.id,
                "batch_number": "BATCH-COMP-001",
                "expiry_date": timezone.now().date() + datetime.timedelta(days=365),
                "quantity_requested": 100,
                "quantity_received": 100,
                "unit_cost": Decimal("50.00"),
                "observation": "Test",
            }
        ]
        orchestrator.register_purchase(purchase_order, details_payload)

        orchestrator.complete_purchase_order(purchase_order)

        purchase_order.refresh_from_db()
        assert purchase_order.status == PurchaseOrder.Status.COMPLETED

        batch = Batch.objects.get(batch_number="BATCH-COMP-001")
        assert batch.status == Batch.BatchStatus.ACTIVE
        assert batch.current_quantity == 100

        movements = InventoryMovement.objects.filter(purchase_order=purchase_order)
        assert movements.count() == 1
        assert movements.first().is_increment is True

    @pytest.mark.django_db
    def test_complete_purchase_order_already_completed(self, orchestrator, purchase_order, supply):

        details_payload = [
            {
                "supply_id": supply.id,
                "batch_number": "BATCH-COMP-002",
                "expiry_date": timezone.now().date() + datetime.timedelta(days=365),
                "quantity_requested": 100,
                "quantity_received": 100,
                "unit_cost": Decimal("50.00"),
                "observation": "Test",
            }
        ]
        orchestrator.register_purchase(purchase_order, details_payload)

        orchestrator.complete_purchase_order(purchase_order)

        initial_movements = InventoryMovement.objects.filter(purchase_order=purchase_order).count()

        orchestrator.complete_purchase_order(purchase_order)

        assert (
            InventoryMovement.objects.filter(purchase_order=purchase_order).count()
            == initial_movements
        )
        assert purchase_order.status == PurchaseOrder.Status.COMPLETED


# ---------------------------------------------------------------------------
# Test PurchaseOrchestrator - Cancel Purchase
# ---------------------------------------------------------------------------


class TestPurchaseOrchestratorCancel:
    @pytest.mark.django_db
    def test_cancel_purchase_order_success(self, orchestrator, purchase_order, supply):

        details_payload = [
            {
                "supply_id": supply.id,
                "batch_number": "BATCH-CANCEL-001",
                "expiry_date": timezone.now().date() + datetime.timedelta(days=365),
                "quantity_requested": 100,
                "quantity_received": 100,
                "unit_cost": Decimal("50.00"),
                "observation": "Test",
            }
        ]
        orchestrator.register_purchase(purchase_order, details_payload)
        orchestrator.complete_purchase_order(purchase_order)

        orchestrator.cancel_purchase_order(purchase_order)

        purchase_order.refresh_from_db()
        assert purchase_order.status == PurchaseOrder.Status.CANCELLED

        batch = Batch.objects.get(batch_number="BATCH-CANCEL-001")
        assert batch.status == Batch.BatchStatus.DISCARDED
        assert batch.current_quantity == 0

        movements = InventoryMovement.objects.filter(purchase_order=purchase_order)
        assert movements.count() == 2
        adjustment_movement = movements.filter(
            movement_type=InventoryMovement.Type.ADJUSTMENT
        ).first()
        assert adjustment_movement is not None
        assert adjustment_movement.is_increment is False

    @pytest.mark.django_db
    def test_cancel_purchase_order_already_cancelled(self, orchestrator, purchase_order):
        purchase_order.status = PurchaseOrder.Status.CANCELLED
        purchase_order.save()

        initial_status = purchase_order.status
        orchestrator.cancel_purchase_order(purchase_order)

        assert purchase_order.status == initial_status


# ---------------------------------------------------------------------------
# Test PurchaseOrchestrator - Status Map
# ---------------------------------------------------------------------------


class TestPurchaseOrchestratorStatusMap:
    @pytest.mark.django_db
    def test_status_map_correct_values(self, orchestrator):
        assert orchestrator.status_map[PurchaseOrder.Status.DRAFT] == Batch.BatchStatus.DISCARDED
        assert orchestrator.status_map[PurchaseOrder.Status.SENT] == Batch.BatchStatus.DISCARDED
        assert orchestrator.status_map[PurchaseOrder.Status.COMPLETED] == Batch.BatchStatus.ACTIVE
        assert (
            orchestrator.status_map[PurchaseOrder.Status.CANCELLED] == Batch.BatchStatus.DISCARDED
        )


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------


class TestPurchaseIntegration:
    @pytest.mark.django_db
    def test_full_purchase_workflow(self, orchestrator, supplier, supply):

        order = PurchaseOrder.objects.create(
            order_number="PO-FULL-001",
            supplier=supplier,
            motive="Full workflow test",
            status=PurchaseOrder.Status.DRAFT,
        )

        # 2. Registrar con stock
        details_payload = [
            {
                "supply_id": supply.id,
                "batch_number": "BATCH-FULL-001",
                "expiry_date": timezone.now().date() + datetime.timedelta(days=365),
                "quantity_requested": 100,
                "quantity_received": 100,
                "unit_cost": Decimal("50.00"),
                "observation": "Test",
            }
        ]
        orchestrator.register_purchase(order, details_payload)

        orchestrator.complete_purchase_order(order)

        order.refresh_from_db()
        assert order.status == PurchaseOrder.Status.COMPLETED

        batch = Batch.objects.get(batch_number="BATCH-FULL-001")
        assert batch.current_quantity == 100
        assert batch.status == Batch.BatchStatus.ACTIVE

        movements = InventoryMovement.objects.filter(purchase_order=order)
        assert movements.count() == 1
        assert movements.first().is_increment is True
        assert movements.first().quantity == 100
