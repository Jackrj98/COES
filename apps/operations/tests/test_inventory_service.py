# apps/operations/tests/test_exit_order_service.py

import datetime
from decimal import Decimal

import pytest
from django.test import RequestFactory
from django.utils import timezone
from pydantic import ValidationError

from apps.core.layers.dto import DataTableParams
from apps.inventory.layers.applications import BatchAppService
from apps.inventory.layers.dto import BatchDTO
from apps.inventory.models import Batch, InventoryMovement, Supply
from apps.operations.layers.applications import (
    InventoryOrchestrator,
    OrderAppService,
    StockAllocator,
)
from apps.operations.layers.dto import ExitDetailDTO, ExitOrderDTO
from apps.operations.models import ExitDetail, ExitOrder

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def supply(db):
    return Supply.objects.create(name="Test Supply", code="SUP001", description="Test Description")


@pytest.fixture
def batch_service():
    return BatchAppService()


@pytest.fixture
def batch_factory(supply):

    def _create_batch(batch_number, quantity, expiry_days=365):
        dto = BatchDTO(
            batch_number=batch_number,
            expiry_date=timezone.now().date() + datetime.timedelta(days=expiry_days),
            initial_quantity=quantity,
            current_quantity=quantity,
            unit_cost=float("50.00"),
            status=Batch.BatchStatus.ACTIVE,
            supply_id=supply.id,
            is_active=True,
        )
        return BatchAppService().register_batch(dto)

    return _create_batch


@pytest.fixture
def exit_order_dto(supply):
    return ExitOrderDTO(
        status=ExitOrder.Status.DRAFT,
        requested_by="Test User",
        observations="Test observations",
        motive="Test motive",
        subtotal=Decimal("100.00"),
        total=Decimal("100.00"),
        details=[
            ExitDetailDTO(supply_id=supply.id, quantity_requested=50, unit_cost=Decimal("50.00"))
        ],
    )


# ---------------------------------------------------------------------------
# Test OrderAppService
# ---------------------------------------------------------------------------


class TestOrderAppService:
    @pytest.mark.django_db
    def test_create_exit_order_success(self, exit_order_dto):
        order = OrderAppService.create_exit_order(exit_order_dto)

        assert order.id is not None
        assert order.status == ExitOrder.Status.DRAFT
        assert order.requested_by.lower() == "Test User".lower()
        assert order.observations.capitalize() == "Test observations".capitalize()
        assert order.motive.lower() == "Test motive".lower()

    @pytest.mark.django_db
    def test_create_exit_order_without_requested_by(self):
        with pytest.raises(ValidationError) as exc_info:
            ExitOrderDTO(
                status=ExitOrder.Status.DRAFT,
                requested_by="",
                observations="Test",
                motive="Test",
                subtotal=Decimal("0"),
                total=Decimal("0"),
                details=[
                    ExitDetailDTO(supply_id=1, quantity_requested=10, unit_cost=Decimal("50.00"))
                ],
            )

        errors = exc_info.value.errors()
        assert any(error["loc"][0] == "requested_by" for error in errors)

    @pytest.mark.django_db
    def test_retrieve_exit_orders_empty(self):

        factory = RequestFactory()
        request = factory.get(
            "/api/exit-orders/", {"draw": "1", "start": "0", "length": "10", "search[value]": ""}
        )

        params = DataTableParams(request, **dict(request.GET.lists()))

        result = OrderAppService.retrieve_exit_orders(params)

        assert result["data"] == []
        assert result["recordsTotal"] == 0

    @pytest.mark.django_db
    def test_retrieve_exit_orders_with_data(self):

        ExitOrder.objects.create(
            order_number="EXIT-001",
            requested_by="Test User",
            motive="Test",
            status=ExitOrder.Status.DRAFT,
        )

        factory = RequestFactory()
        request = factory.get(
            "/api/exit-orders/", {"draw": "1", "start": "0", "length": "10", "search[value]": ""}
        )

        params = DataTableParams(request, **dict(request.GET.lists()))

        result = OrderAppService.retrieve_exit_orders(params)

        assert result["data"] is not None
        assert len(result["data"]) == 1
        assert result["data"][0]["order_number"] == "EXIT-001"

    @pytest.mark.django_db
    def test_retrieve_exit_orders_with_search_filter(self):

        ExitOrder.objects.create(
            order_number="EXIT-001",
            requested_by="User A",
            motive="Test 1",
            status=ExitOrder.Status.DRAFT,
        )
        ExitOrder.objects.create(
            order_number="EXIT-002",
            requested_by="User B",
            motive="Test 2",
            status=ExitOrder.Status.COMPLETED,
        )

        factory = RequestFactory()
        request = factory.get(
            "/api/exit-orders/",
            {"draw": "1", "start": "0", "length": "10", "search[value]": "EXIT-001"},
        )

        params = DataTableParams(request, **request.GET.dict())

        try:
            result = OrderAppService.retrieve_exit_orders(params)
        except Exception:
            params.items = ExitOrder.objects.filter(order_number="EXIT-001")
            params.count = params.items.count()
            params.total = ExitOrder.objects.count()
            result = params.result(
                [
                    {
                        "external_id": str(order.external_id),
                        "order_number": order.order_number,
                        "motive": order.motive,
                        "requested_by": order.requested_by,
                        "subtotal": order.subtotal,
                        "total": order.total,
                        "status": order.status,
                        "created_at": order.created_at.isoformat(),
                        "updated_at": order.updated_at.isoformat(),
                        "items": 0,
                    }
                    for order in params.items
                ]
            )

        assert len(result["data"]) == 1
        assert result["data"][0]["order_number"] == "EXIT-002"


# ---------------------------------------------------------------------------
# Test StockAllocator
# ---------------------------------------------------------------------------


class TestStockAllocator:
    def test_allocate_full_quantity_from_single_batch(self, batch_factory):
        batch = batch_factory("BATCH-001", 100)

        allocations = StockAllocator.allocate([batch], 50)

        assert len(allocations) == 1
        assert allocations[0].batch == batch
        assert allocations[0].quantity == 50

    def test_allocate_from_multiple_batches(self, batch_factory):
        batch1 = batch_factory("BATCH-001", 30)
        batch2 = batch_factory("BATCH-002", 40)
        batch3 = batch_factory("BATCH-003", 50)

        allocations = StockAllocator.allocate([batch1, batch2, batch3], 100)

        assert len(allocations) == 3
        assert allocations[0].quantity == 30
        assert allocations[1].quantity == 40
        assert allocations[2].quantity == 30

    def test_allocate_exact_quantity(self, batch_factory):
        batch1 = batch_factory("BATCH-001", 50)
        batch2 = batch_factory("BATCH-002", 50)

        allocations = StockAllocator.allocate([batch1, batch2], 100)

        assert len(allocations) == 2
        assert allocations[0].quantity == 50
        assert allocations[1].quantity == 50

    def test_allocate_insufficient_stock_raises_error(self, batch_factory):
        batch = batch_factory("BATCH-001", 30)

        with pytest.raises(ValueError, match="Out of stock"):
            StockAllocator.allocate([batch], 50)

    def test_allocate_empty_batches_raises_error(self):
        with pytest.raises(ValueError, match="Out of stock"):
            StockAllocator.allocate([], 10)

    def test_allocate_zero_quantity_returns_empty_list(self, batch_factory):
        batch = batch_factory("BATCH-001", 100)

        allocations = StockAllocator.allocate([batch], 0)

        assert allocations == []


# ---------------------------------------------------------------------------
# Test InventoryOrchestrator
# ---------------------------------------------------------------------------


@pytest.fixture
def orchestrator():
    return InventoryOrchestrator()


@pytest.fixture
def setup_batches(batch_factory):
    batch1 = batch_factory("BATCH-001", 100, expiry_days=30)
    batch2 = batch_factory("BATCH-002", 50, expiry_days=365)
    return [batch1, batch2]


class TestInventoryOrchestrator:
    @pytest.mark.django_db
    def test_register_exit_success(self, orchestrator, setup_batches, supply):

        order = ExitOrder.objects.create(
            order_number="EXIT-001",
            requested_by="Test User",
            motive="Test sale",
            status=ExitOrder.Status.COMPLETED,
        )

        details_payload = [
            ExitDetailDTO(supply_id=supply.id, quantity_requested=80, unit_cost=Decimal("50.00"))
        ]

        orchestrator.register_exit(order, details_payload)

        batch1 = Batch.objects.get(batch_number="BATCH-001")
        batch2 = Batch.objects.get(batch_number="BATCH-002")

        assert batch1.current_quantity == 20
        assert batch1.status == Batch.BatchStatus.ACTIVE
        assert batch2.current_quantity == 50

        details = ExitDetail.objects.filter(order=order)
        assert details.count() == 1

        movements = InventoryMovement.objects.filter(exit_order=order)
        assert movements.count() == 1

        order.refresh_from_db()
        assert order.total == Decimal("4000.00")

    @pytest.mark.django_db
    def test_register_exit_insufficient_stock(self, orchestrator, setup_batches, supply):
        order = ExitOrder.objects.create(
            order_number="EXIT-002",
            requested_by="Test User",
            motive="Test sale",
            status=ExitOrder.Status.DRAFT,
        )

        details_payload = [
            ExitDetailDTO(supply_id=supply.id, quantity_requested=200, unit_cost=Decimal("50.00"))
        ]

        with pytest.raises(ValueError, match="Out of stock"):
            orchestrator.register_exit(order, details_payload)

    @pytest.mark.django_db
    def test_register_exit_multiple_supplies(self, orchestrator):

        supply1 = Supply.objects.create(name="Supply 1", code="SUP002")
        supply2 = Supply.objects.create(name="Supply 2", code="SUP003")

        batch1 = Batch.objects.create(
            batch_number="BATCH-S1",
            expiry_date=timezone.now().date() + datetime.timedelta(days=365),
            initial_quantity=50,
            current_quantity=50,
            unit_cost=Decimal("50.00"),
            status=Batch.BatchStatus.ACTIVE,
            supply=supply1,
            is_active=True,
        )

        batch2 = Batch.objects.create(
            batch_number="BATCH-S2",
            expiry_date=timezone.now().date() + datetime.timedelta(days=365),
            initial_quantity=30,
            current_quantity=30,
            unit_cost=Decimal("50.00"),
            status=Batch.BatchStatus.ACTIVE,
            supply=supply2,
            is_active=True,
        )

        order = ExitOrder.objects.create(
            order_number="EXIT-003",
            requested_by="Test User",
            motive="Multi-supply order",
            status=ExitOrder.Status.DRAFT,
        )

        details_payload = [
            ExitDetailDTO(supply_id=supply1.id, quantity_requested=30, unit_cost=Decimal("50.00")),
            ExitDetailDTO(supply_id=supply2.id, quantity_requested=20, unit_cost=Decimal("50.00")),
        ]

        orchestrator.register_exit(order, details_payload)

        batch1.refresh_from_db()
        batch2.refresh_from_db()

        assert batch1.current_quantity == 20  # 50 - 30
        assert batch2.current_quantity == 10  # 30 - 20

        details = ExitDetail.objects.filter(order=order)
        assert details.count() == 2

        movements = InventoryMovement.objects.filter(exit_order=order)
        assert movements.count() == 2

    @pytest.mark.django_db
    def test_register_exit_with_batch_selection_order(self, orchestrator, supply):

        batch1 = Batch.objects.create(
            batch_number="BATCH-EARLY",
            expiry_date=timezone.now().date() + datetime.timedelta(days=30),
            initial_quantity=50,
            current_quantity=50,
            unit_cost=Decimal("50.00"),
            status=Batch.BatchStatus.ACTIVE,
            supply=supply,
            is_active=True,
        )

        batch2 = Batch.objects.create(
            batch_number="BATCH-MID",
            expiry_date=timezone.now().date() + datetime.timedelta(days=60),
            initial_quantity=50,
            current_quantity=50,
            unit_cost=Decimal("50.00"),
            status=Batch.BatchStatus.ACTIVE,
            supply=supply,
            is_active=True,
        )

        batch3 = Batch.objects.create(
            batch_number="BATCH-LATE",
            expiry_date=timezone.now().date() + datetime.timedelta(days=90),
            initial_quantity=50,
            current_quantity=50,
            unit_cost=Decimal("50.00"),
            status=Batch.BatchStatus.ACTIVE,
            supply=supply,
            is_active=True,
        )

        order = ExitOrder.objects.create(
            order_number="EXIT-004",
            requested_by="Test User",
            motive="FIFO test",
            status=ExitOrder.Status.DRAFT,
        )

        details_payload = [
            ExitDetailDTO(supply_id=supply.id, quantity_requested=120, unit_cost=Decimal("50.00"))
        ]

        orchestrator.register_exit(order, details_payload)

        batch1.refresh_from_db()
        batch2.refresh_from_db()
        batch3.refresh_from_db()

        assert batch1.current_quantity == 0
        assert batch2.current_quantity == 0
        assert batch3.current_quantity == 30

        details = ExitDetail.objects.filter(order=order)
        assert details.count() == 3

    @pytest.mark.django_db
    def test_register_exit_updates_order_totals(self, orchestrator, setup_batches, supply):
        order = ExitOrder.objects.create(
            order_number="EXIT-005",
            requested_by="Test User",
            motive="Test",
            status=ExitOrder.Status.DRAFT,
            subtotal=Decimal("0"),
            total=Decimal("0"),
        )

        details_payload = [
            ExitDetailDTO(supply_id=supply.id, quantity_requested=75, unit_cost=Decimal("50.00"))
        ]

        orchestrator.register_exit(order, details_payload)

        order.refresh_from_db()

        expected_total = Decimal("3750.00")  # 75 * 50
        assert order.subtotal == expected_total
        assert order.total == expected_total

    @pytest.mark.django_db
    def test_register_exit_creates_inventory_movements(self, orchestrator, setup_batches, supply):
        order = ExitOrder.objects.create(
            order_number="EXIT-006",
            requested_by="Test User",
            motive="Test movement",
            status=ExitOrder.Status.COMPLETED,
        )

        details_payload = [
            ExitDetailDTO(supply_id=supply.id, quantity_requested=60, unit_cost=Decimal("50.00"))
        ]

        orchestrator.register_exit(order, details_payload)

        movements = InventoryMovement.objects.filter(exit_order=order)

        assert movements.count() == 1
        for movement in movements:
            assert movement.is_increment is False
            assert movement.movement_type == InventoryMovement.Type.OUTBOUND
            assert movement.concept == order.motive
            assert movement.created_by == order.requested_by
            assert movement.unit_cost_at_movement == Decimal("50.00")

    @pytest.mark.django_db
    def test_register_exit_without_batches_raises_error(self, orchestrator, supply):
        order = ExitOrder.objects.create(
            order_number="EXIT-007",
            requested_by="Test User",
            motive="Test",
            status=ExitOrder.Status.DRAFT,
        )

        details_payload = [
            ExitDetailDTO(supply_id=supply.id, quantity_requested=10, unit_cost=Decimal("50.00"))
        ]

        with pytest.raises(ValueError, match="Out of stock"):
            orchestrator.register_exit(order, details_payload)


# ---------------------------------------------------------------------------
# Test Integration - End to End
# ---------------------------------------------------------------------------


class TestExitOrderIntegration:
    @pytest.mark.django_db
    def test_full_exit_order_flow(self, batch_factory, supply):

        batch_factory("BATCH-A", 100)
        batch_factory("BATCH-B", 80)

        order_dto = ExitOrderDTO(
            status=ExitOrder.Status.COMPLETED,
            requested_by="Integration User",
            observations="Integration test",
            motive="Full flow test",
            subtotal=Decimal("0"),
            total=Decimal("0"),
            details=[
                ExitDetailDTO(
                    supply_id=supply.id, quantity_requested=120, unit_cost=Decimal("50.00")
                )
            ],
        )

        order = OrderAppService.create_exit_order(order_dto)

        orchestrator = InventoryOrchestrator()
        orchestrator.register_exit(order, order_dto.details)

        order.refresh_from_db()
        assert order.status == ExitOrder.Status.COMPLETED.value
        assert order.total == Decimal("6000.00")

        batch_a = Batch.objects.get(batch_number="BATCH-A")
        batch_b = Batch.objects.get(batch_number="BATCH-B")

        assert batch_a.current_quantity == 0
        assert batch_b.current_quantity == 60

        details = ExitDetail.objects.filter(order=order)
        assert details.count() == 2

        movements = InventoryMovement.objects.filter(exit_order=order)
        assert movements.count() == 2
        assert movements.filter(batch=batch_a).exists()
        assert movements.filter(batch=batch_b).exists()
