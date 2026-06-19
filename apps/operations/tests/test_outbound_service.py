# tests/operations/test_outbound_service.py
import uuid
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from django.core.exceptions import ValidationError

from apps.catalogs.models import Catalog, CatalogItem
from apps.inventory.models import Batch, InventoryMovement, Supply
from apps.operations.layers.applications.outbound_service import (
    OutboundOrderService,
    StockAllocation,
)
from apps.operations.models import InventoryOrder, OrderDetail, OutboundOrder, Supplier
from apps.security.models import User


@pytest.mark.django_db
class TestOutboundOrderService:
    @pytest.fixture
    def service(self):
        return OutboundOrderService()

    @pytest.fixture
    def supplier(self):
        return Supplier.objects.create(
            business_name="Test Supplier",
            first_name="John",
            last_name="Doe",
            document_number="123456789",
        )

    @pytest.fixture(scope="function", autouse=True)
    def setup_required_catalogs(self, django_db_blocker):
        """Setup required catalogs for tests."""
        with django_db_blocker.unblock():
            catalogs_data = [
                {
                    "code": Catalog.CatalogCodes.SUPPLY_CATEGORY,
                    "name": "Categorias",
                    "description": "Categorías para suministros",
                    "priority": 1,
                },
                {
                    "code": Catalog.CatalogCodes.UNIT_OF_MEASURE,
                    "name": "Unidades de Medida",
                    "description": "Unidades de medida para suministros",
                    "priority": 2,
                },
            ]

            for catalog_data in catalogs_data:
                Catalog.objects.get_or_create(code=catalog_data["code"], defaults=catalog_data)

    @pytest.fixture
    def supply_category_catalog(self):
        return Catalog.objects.get(code=Catalog.CatalogCodes.SUPPLY_CATEGORY)

    @pytest.fixture
    def unit_of_measure_catalog(self):
        return Catalog.objects.get(code=Catalog.CatalogCodes.UNIT_OF_MEASURE)

    @pytest.fixture
    def category(self, supply_category_catalog):
        category_item, _ = CatalogItem.objects.get_or_create(
            catalog=supply_category_catalog,
            code="MED-SUP",
            defaults={"name": "Insumos Médicos", "priority": 1},
        )
        return category_item

    @pytest.fixture
    def uom(self, unit_of_measure_catalog):
        uom_item, _ = CatalogItem.objects.get_or_create(
            catalog=unit_of_measure_catalog,
            code="UNI",
            defaults={"name": "Unidad", "priority": 1},
        )
        return uom_item

    @pytest.fixture
    def supply(self, category, uom):
        unique_id = uuid.uuid4().hex[:6]
        return Supply.objects.create(
            name=f"Suministro {unique_id}",
            code=f"SUP-{unique_id}",
            barcode=f"BC-{unique_id}",
            description="Descripción de prueba",
            is_active=True,
            stock_min=10,
            stock_max=100,
            category=category,
            unit_of_measure=uom,
        )

    @pytest.fixture
    def batch(self, supply, supplier):
        number = f"LOT-{uuid.uuid4().hex[:6]}"
        return Batch.objects.create(
            batch_number=number,
            supply=supply,
            supplier=supplier,
            initial_quantity=100,
            current_quantity=100,
            unit_cost=Decimal("10.00"),
            expiry_date=date.today() + timedelta(days=365),
            status=Batch.BatchStatus.ACTIVE,
            is_active=True,
        )

    @pytest.fixture
    def batch_with_low_stock(self, supply, supplier):
        number = f"LOT-{uuid.uuid4().hex[:6]}"
        return Batch.objects.create(
            batch_number=number,
            supply=supply,
            supplier=supplier,
            initial_quantity=10,
            current_quantity=10,
            unit_cost=Decimal("10.00"),
            expiry_date=date.today() + timedelta(days=365),
            status=Batch.BatchStatus.ACTIVE,
            is_active=True,
        )

    @pytest.fixture
    def outbound_order(self, supplier):
        return OutboundOrder.objects.create(
            order_number="OUT-2026-0001",
            motive="Test dispatch order",
            supplier=supplier,
            scheduled_date=date.today() + timedelta(days=7),
            status=OutboundOrder.StatusType.COMPLETED,
        )

    @pytest.fixture
    def user(self):
        return User.objects.create_user(
            username="testuser",
            email="test@coes.com",
            password="testpass123",
        )

    # ============ TESTS: get_outbound_orders ============

    def test_get_outbound_orders_success(self, service, outbound_order):
        """Test retrieving outbound orders successfully."""
        params = Mock()
        params.items = OutboundOrder.objects.all()
        params.result = Mock(return_value=[])

        with patch(
            "apps.operations.layers.applications.outbound_service.DatatableSearch.retrieve_outbound_orders"
        ) as mock_retrieve:
            result = service.get_outbound_orders(params)

            assert result == params.result.return_value
            mock_retrieve.assert_called_once_with(params)

    def test_get_outbound_orders_failure(self, service):
        """Test retrieving outbound orders with error."""
        params = Mock()
        params.items = Mock()
        params.items.annotate = Mock(side_effect=Exception("Database error"))

        result = service.get_outbound_orders(params)

        assert result == []

    # ============ TESTS: save_outbound_order ============

    def test_save_outbound_order_success(self, service, supplier, supply, batch, user):
        """Test creating a new outbound order successfully."""
        payload = {
            "order_type": OutboundOrder.OrderType.OUTBOUND,
            "motive": "Test dispatch",
            "status": OutboundOrder.StatusType.COMPLETED,
            "observations": "Test observations",
        }
        line_details = [
            {
                "supply_id": supply.id,
                "quantity_requested": 10,
            }
        ]

        with patch.object(service.batch_service, "retrieve_by_expiry_date") as mock_retrieve:
            mock_retrieve.return_value = Batch.objects.filter(id=batch.id)

            result = service.save_outbound_order(
                OutboundOrder(),
                payload,
                line_details,
                user,
            )

            assert result is not None
            assert result.order_number.startswith("OU-")
            assert result.motive == "Test dispatch"
            assert result.status == OutboundOrder.StatusType.COMPLETED
            assert result.details.count() == 1

            detail = result.details.first()
            assert detail.supply.id == supply.id
            assert detail.quantity_requested == 10
            assert detail.quantity_fulfilled == 10

            # Verify batch was updated
            batch.refresh_from_db()
            assert batch.current_quantity == 90

            # Verify movement was created
            movement = InventoryMovement.objects.filter(batch=batch).first()
            assert movement is not None
            assert movement.quantity == 10
            assert movement.movement_type == InventoryMovement.Type.OUTBOUND

    def test_save_outbound_order_missing_required_fields(self, service):
        """Test creating order with missing required fields."""
        payload = {
            "order_type": OutboundOrder.OrderType.OUTBOUND,
            "status": OutboundOrder.StatusType.COMPLETED,
        }
        line_details = []

        with pytest.raises(ValidationError) as excinfo:
            service.save_outbound_order(
                InventoryOrder(order_type=OutboundOrder.OrderType.OUTBOUND),
                payload,
                line_details,
                None,
            )

        assert "motive" in str(excinfo.value)

    def test_save_outbound_order_insufficient_stock(
        self, service, supply, batch_with_low_stock, user
    ):
        """Test creating order with insufficient stock."""
        payload = {
            "order_type": OutboundOrder.OrderType.OUTBOUND,
            "motive": "Test dispatch",
            "status": OutboundOrder.StatusType.COMPLETED,
        }
        line_details = [
            {
                "supply_id": supply.id,
                "quantity_requested": 20,  # More than available (10)
            }
        ]

        with patch.object(service.batch_service, "retrieve_by_expiry_date") as mock_retrieve:
            mock_retrieve.return_value = Batch.objects.filter(id=batch_with_low_stock.id)

            with pytest.raises(ValueError) as excinfo:
                service.save_outbound_order(
                    OutboundOrder(),
                    payload,
                    line_details,
                    user,
                )

            assert "Out of stock" in str(excinfo.value)

    def test_save_outbound_order_multiple_batches(self, service, supply, supplier, user):
        """Test creating order that uses multiple batches."""
        # Create multiple batches
        batch1 = Batch.objects.create(
            batch_number=f"LOT-{uuid.uuid4().hex[:6]}",
            supply=supply,
            supplier=supplier,
            initial_quantity=10,
            current_quantity=10,
            unit_cost=Decimal("10.00"),
            expiry_date=date.today() + timedelta(days=365),
            status=Batch.BatchStatus.ACTIVE,
            is_active=True,
        )
        batch2 = Batch.objects.create(
            batch_number=f"LOT-{uuid.uuid4().hex[:6]}",
            supply=supply,
            supplier=supplier,
            initial_quantity=10,
            current_quantity=10,
            unit_cost=Decimal("12.00"),
            expiry_date=date.today() + timedelta(days=300),
            status=Batch.BatchStatus.ACTIVE,
            is_active=True,
        )

        payload = {
            "order_type": OutboundOrder.OrderType.OUTBOUND,
            "motive": "Test dispatch",
            "status": OutboundOrder.StatusType.COMPLETED,
        }
        line_details = [
            {
                "supply_id": supply.id,
                "quantity_requested": 15,  # Will use batch1 (10) + batch2 (5)
            }
        ]

        with patch.object(service.batch_service, "retrieve_by_expiry_date") as mock_retrieve:
            mock_retrieve.return_value = Batch.objects.filter(id__in=[batch1.id, batch2.id])

            result = service.save_outbound_order(
                OutboundOrder(),
                payload,
                line_details,
                user,
            )

            assert result.details.count() == 2  # One per batch

            # Verify batches were updated
            batch1.refresh_from_db()
            batch2.refresh_from_db()
            assert batch1.current_quantity == 0
            assert batch1.status == Batch.BatchStatus.DEPLETED
            assert batch2.current_quantity == 5

            # Verify movements
            movements = InventoryMovement.objects.filter(inventory_order=result).order_by(
                "batch__id"
            )
            assert movements.count() == 2
            assert movements[0].quantity == 10
            assert movements[1].quantity == 5

    def test_save_outbound_order_without_user(self, service, supply, batch, user):
        """Test creating order without a user (should use 'system' as created_by)."""
        payload = {
            "order_type": OutboundOrder.OrderType.OUTBOUND,
            "motive": "Test dispatch",
            "status": OutboundOrder.StatusType.COMPLETED,
        }
        line_details = [
            {
                "supply_id": supply.id,
                "quantity_requested": 10,
            }
        ]

        with patch.object(service.batch_service, "retrieve_by_expiry_date") as mock_retrieve:
            mock_retrieve.return_value = Batch.objects.filter(id=batch.id)

            result = service.save_outbound_order(
                OutboundOrder(),
                payload,
                line_details,
                None,
            )

            assert result.created_by == "system"

    # ============ TESTS: allocate ============

    def test_allocate_success(self, service, batch):
        """Test allocating quantity from batches successfully."""
        batches = [batch]
        quantity = 10

        allocations = service.allocate(batches, quantity)

        assert len(allocations) == 1
        assert allocations[0].batch == batch
        assert allocations[0].quantity == 10

    def test_allocate_multiple_batches(self, service, supply, supplier):
        """Test allocating quantity from multiple batches."""
        batch1 = Batch.objects.create(
            batch_number=f"LOT-{uuid.uuid4().hex[:6]}",
            supply=supply,
            supplier=supplier,
            initial_quantity=10,
            current_quantity=10,
            unit_cost=Decimal("10.00"),
            expiry_date=date.today() + timedelta(days=365),
            status=Batch.BatchStatus.ACTIVE,
            is_active=True,
        )
        batch2 = Batch.objects.create(
            batch_number=f"LOT-{uuid.uuid4().hex[:6]}",
            supply=supply,
            supplier=supplier,
            initial_quantity=5,
            current_quantity=5,
            unit_cost=Decimal("12.00"),
            expiry_date=date.today() + timedelta(days=300),
            status=Batch.BatchStatus.ACTIVE,
            is_active=True,
        )

        batches = [batch1, batch2]
        quantity = 12

        allocations = service.allocate(batches, quantity)

        assert len(allocations) == 2
        assert allocations[0].batch == batch1
        assert allocations[0].quantity == 10
        assert allocations[1].batch == batch2
        assert allocations[1].quantity == 2

    def test_allocate_exact_quantity(self, service, batch):
        """Test allocating exact quantity available."""
        batches = [batch]
        quantity = 100

        allocations = service.allocate(batches, quantity)

        assert len(allocations) == 1
        assert allocations[0].quantity == 100

    def test_allocate_insufficient_stock(self, service, batch):
        """Test allocating with insufficient stock."""
        batches = [batch]
        quantity = 150

        with pytest.raises(ValueError) as excinfo:
            service.allocate(batches, quantity)

        assert "Out of stock" in str(excinfo.value)

    def test_allocate_zero_quantity(self, service, batch):
        """Test allocating zero quantity."""
        batches = [batch]
        quantity = 0

        allocations = service.allocate(batches, quantity)

        assert len(allocations) == 0

    # ============ TESTS: _consolidate ============

    def test_consolidate_single_item(self, service):
        """Test consolidating details with single item."""
        details = [
            {"supply_id": 1, "quantity_requested": 10},
        ]

        result = service._consolidate(details)

        assert result == {1: 10}

    def test_consolidate_multiple_items(self, service):
        """Test consolidating details with multiple items."""
        details = [
            {"supply_id": 1, "quantity_requested": 10},
            {"supply_id": 2, "quantity_requested": 5},
            {"supply_id": 1, "quantity_requested": 3},
        ]

        result = service._consolidate(details)

        assert result == {1: 13, 2: 5}

    def test_consolidate_empty(self, service):
        """Test consolidating empty list."""
        result = service._consolidate([])

        assert result == {}

    # ============ TESTS: _build_detail ============

    def test_build_detail(self, service, outbound_order, batch):
        """Test building order detail."""
        alloc = StockAllocation(batch=batch, quantity=10)

        detail = service._build_detail(outbound_order, alloc)

        assert detail.inventory_order == outbound_order
        assert detail.supply_id == batch.supply_id
        assert detail.batch == batch
        assert detail.quantity_requested == 10
        assert detail.quantity_fulfilled == 10
        assert detail.unit_cost == batch.unit_cost
        assert detail.observations == (outbound_order.observations or "")

    def test_build_detail_with_observations(self, service, outbound_order, batch):
        """Test building order detail with observations."""
        outbound_order.observations = "Test observations"
        alloc = StockAllocation(batch=batch, quantity=10)

        detail = service._build_detail(outbound_order, alloc)

        assert detail.observations == "Test observations"

    # ============ TESTS: _build_movement ============

    def test_build_movement(self, service, outbound_order, batch):
        """Test building inventory movement."""
        old_stock = 100
        alloc = StockAllocation(batch=batch, quantity=10)
        outbound_order.created_by = "testuser"

        movement = service._build_movement(outbound_order, alloc, old_stock)

        assert movement.batch == batch
        assert movement.is_increment is False
        assert movement.concept == outbound_order.motive
        assert movement.quantity == 10
        assert movement.previous_stock == 100
        assert movement.after_stock == 90
        assert movement.unit_cost_at_movement == batch.unit_cost
        assert movement.movement_type == InventoryMovement.Type.OUTBOUND
        assert movement.created_by == outbound_order.created_by
        assert movement.inventory_order == outbound_order

    # ============ TESTS: _bulk_persist ============

    def test_bulk_persist(self, service, outbound_order, batch):
        """Test bulk persisting batches, details, and movements."""
        batch.current_quantity = 90
        batches_to_update = [batch]
        details_to_create = [
            OrderDetail(
                inventory_order=outbound_order,
                supply_id=batch.supply_id,
                batch=batch,
                quantity_requested=10,
                quantity_fulfilled=10,
                unit_cost=batch.unit_cost,
            )
        ]
        movements_to_create = [
            InventoryMovement(
                batch=batch,
                is_increment=False,
                concept="Test movement",
                quantity=10,
                previous_stock=100,
                after_stock=90,
                unit_cost_at_movement=batch.unit_cost,
                movement_type=InventoryMovement.Type.OUTBOUND,
                inventory_order=outbound_order,
            )
        ]

        service._bulk_persist(batches_to_update, details_to_create, movements_to_create)

        # Verify batch was updated
        batch.refresh_from_db()
        assert batch.current_quantity == 90

        # Verify detail was created
        assert OrderDetail.objects.filter(inventory_order=outbound_order).count() == 1

        # Verify movement was created
        assert InventoryMovement.objects.filter(inventory_order=outbound_order).count() == 1

    # ============ TESTS: register_outbound ============

    def test_register_outbound_success(self, service, outbound_order, supply, batch, user):
        """Test registering outbound order."""
        details_payload = [{"supply_id": supply.id, "quantity_requested": 10}]

        with patch.object(service.batch_service, "retrieve_by_expiry_date") as mock_retrieve:
            mock_retrieve.return_value = Batch.objects.filter(id=batch.id)

            service.register_outbound(outbound_order, details_payload)

            # Verify batch was updated
            batch.refresh_from_db()
            assert batch.current_quantity == 90

            # Verify detail was created
            detail = OrderDetail.objects.filter(inventory_order=outbound_order).first()
            assert detail is not None
            assert detail.quantity_requested == 10

            # Verify movement was created
            movement = InventoryMovement.objects.filter(inventory_order=outbound_order).first()
            assert movement is not None
            assert movement.quantity == 10

    def test_register_outbound_consolidates_details(
        self, service, outbound_order, supply, batch, user
    ):
        """Test that register_outbound consolidates details by supply_id."""
        details_payload = [
            {"supply_id": supply.id, "quantity_requested": 5},
            {"supply_id": supply.id, "quantity_requested": 5},
        ]

        with patch.object(service.batch_service, "retrieve_by_expiry_date") as mock_retrieve:
            mock_retrieve.return_value = Batch.objects.filter(id=batch.id)

            service.register_outbound(outbound_order, details_payload)

            # Should have only one detail (consolidated)
            details = OrderDetail.objects.filter(inventory_order=outbound_order)
            assert details.count() == 1
            assert details.first().quantity_requested == 10

    def test_register_outbound_handles_multiple_supplies(
        self, service, outbound_order, supplier, user, category, unit_of_measure_catalog
    ):
        """Test registering outbound with multiple supplies."""
        # Create two supplies and batches
        supply1 = Supply.objects.create(
            name=f"Supply1-{uuid.uuid4().hex[:6]}",
            code=f"SUP1-{uuid.uuid4().hex[:6]}",
            description="Supply 1",
            is_active=True,
            category_id=category.id,
            unit_of_measure_id=unit_of_measure_catalog.id,
        )
        supply2 = Supply.objects.create(
            name=f"Supply2-{uuid.uuid4().hex[:6]}",
            code=f"SUP2-{uuid.uuid4().hex[:6]}",
            description="Supply 2",
            is_active=True,
            category_id=category.id,
            unit_of_measure_id=unit_of_measure_catalog.id,
        )

        batch1 = Batch.objects.create(
            batch_number=f"LOT-{uuid.uuid4().hex[:6]}",
            supply=supply1,
            supplier=supplier,
            initial_quantity=10,
            current_quantity=10,
            unit_cost=Decimal("10.00"),
            expiry_date=date.today() + timedelta(days=365),
            status=Batch.BatchStatus.ACTIVE,
            is_active=True,
        )
        batch2 = Batch.objects.create(
            batch_number=f"LOT-{uuid.uuid4().hex[:6]}",
            supply=supply2,
            supplier=supplier,
            initial_quantity=10,
            current_quantity=10,
            unit_cost=Decimal("12.00"),
            expiry_date=date.today() + timedelta(days=365),
            status=Batch.BatchStatus.ACTIVE,
            is_active=True,
        )

        details_payload = [
            {"supply_id": supply1.id, "quantity_requested": 5},
            {"supply_id": supply2.id, "quantity_requested": 3},
        ]

        with patch.object(service.batch_service, "retrieve_by_expiry_date") as mock_retrieve:

            def side_effect(supply_id):
                if supply_id == supply1.id:
                    return Batch.objects.filter(id=batch1.id)
                elif supply_id == supply2.id:
                    return Batch.objects.filter(id=batch2.id)
                return Batch.objects.none()

            mock_retrieve.side_effect = side_effect

            service.register_outbound(outbound_order, details_payload)

            # Verify both supplies were processed
            details = OrderDetail.objects.filter(inventory_order=outbound_order)
            assert details.count() == 2
            assert details.filter(supply_id=supply1.id).first().quantity_requested == 5
            assert details.filter(supply_id=supply2.id).first().quantity_requested == 3

    # ============ TESTS: _build_order_from_payload ============

    def test_build_order_from_payload_success(self, service):
        """Test building order from payload."""
        builder = Mock()
        payload = {
            "order_type": OutboundOrder.OrderType.OUTBOUND,
            "motive": "Test dispatch",
            "status": OutboundOrder.StatusType.COMPLETED,
            "observations": "Test observations",
        }

        service._build_order_from_payload(builder, payload)

        builder.set_order_type.assert_called_with(payload["order_type"])
        builder.set_motive.assert_called_with(payload["motive"])
        builder.set_status.assert_called_with(payload["status"])
        builder.set_observations.assert_called_with(payload["observations"])

    def test_build_order_from_payload_missing_motive(self, service):
        """Test building order with missing motive."""
        builder = Mock()
        payload = {
            "order_type": OutboundOrder.OrderType.OUTBOUND,
            "status": OutboundOrder.StatusType.COMPLETED,
        }

        with pytest.raises(ValidationError) as excinfo:
            service._build_order_from_payload(builder, payload)

        assert "motive" in str(excinfo.value)

    def test_build_order_from_payload_without_observations(self, service):
        """Test building order without observations."""
        builder = Mock()
        payload = {
            "order_type": OutboundOrder.OrderType.OUTBOUND,
            "motive": "Test dispatch",
            "status": OutboundOrder.StatusType.COMPLETED,
        }

        service._build_order_from_payload(builder, payload)

        builder.set_order_type.assert_called_with(payload["order_type"])
        builder.set_motive.assert_called_with(payload["motive"])
        builder.set_status.assert_called_with(payload["status"])
        builder.set_observations.assert_not_called()

    # ============ TESTS: Exception handling ============

    def test_save_outbound_order_validation_error(self, service, user):
        """Test save_outbound_order handles ValidationError."""
        payload = {
            "order_type": OutboundOrder.OrderType.OUTBOUND,
            "status": OutboundOrder.StatusType.COMPLETED,
        }
        line_details = []

        with pytest.raises(ValidationError):
            service.save_outbound_order(
                InventoryOrder(order_type=OutboundOrder.OrderType.OUTBOUND),
                payload,
                line_details,
                user,
            )

    def test_save_outbound_order_unexpected_error(self, service, user):
        """Test save_outbound_order handles unexpected errors."""
        payload = {
            "order_type": OutboundOrder.OrderType.OUTBOUND,
            "motive": "Test dispatch",
            "status": OutboundOrder.StatusType.COMPLETED,
        }
        line_details = [{"supply_id": 1, "quantity_requested": 10}]

        with patch.object(service.batch_service, "retrieve_by_expiry_date") as mock_retrieve:
            mock_retrieve.side_effect = Exception("Unexpected database error")

            with pytest.raises(Exception):
                service.save_outbound_order(
                    InventoryOrder(order_type=OutboundOrder.OrderType.OUTBOUND),
                    payload,
                    line_details,
                    user,
                )
