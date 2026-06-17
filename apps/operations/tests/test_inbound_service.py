# tests/operations/test_inbound_service.py
import uuid
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from django.core.exceptions import ValidationError

from apps.catalogs.models import Catalog, CatalogItem
from apps.inventory.models import Batch, InventoryMovement, Supply
from apps.operations.layers.applications.inbound_service import InboundOrderService
from apps.operations.models import InboundOrder, InventoryOrder, OrderDetail, Supplier
from apps.security.models import User


@pytest.mark.django_db
class TestInboundOrderService:
    @pytest.fixture
    def service(self):
        return InboundOrderService()

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
    def inbound_order(self, supplier):
        return InboundOrder.objects.create(
            order_number="IN-2026-0001",
            order_type=InventoryOrder.OrderType.INBOUND,
            motive="Test purchase order",
            supplier=supplier,
            scheduled_date=date.today() + timedelta(days=7),
            status=InventoryOrder.StatusType.SENT,
        )

    @pytest.fixture
    def order_payload(self, supplier):
        return {
            "order_type": InventoryOrder.OrderType.INBOUND,
            "motive": "Test purchase order",
            "status": InventoryOrder.StatusType.SENT,
            "supplier": supplier.id,
            "scheduled_date": date.today() + timedelta(days=7),
            "observations": "Test observations",
            "received_date": None,
        }

    @pytest.fixture
    def line_details(self, supply):
        return [
            {
                "supply_id": supply.id,
                "batch_number": "LOTE-001",
                "expiry_date": date.today() + timedelta(days=365),
                "quantity_requested": 10,
                "quantity_fulfilled": 0,
                "unit_cost": Decimal("10.00"),
                "observations": "Test line detail",
            }
        ]

    @pytest.fixture
    def user(self):
        return User.objects.create_user(
            username="testuser",
            email="test@coes.com",
            password="testpass123",
        )

    @pytest.fixture
    def user_without_email(self):
        return User.objects.create_user(
            username="testuser2", password="testpass123", first_name="Test", last_name="User2"
        )

    # ============ TESTS: get_inbound_orders ============

    def test_get_inbound_orders_success(self, service, inbound_order):
        """Test it retrieving inbound orders successfully."""
        params = Mock()
        params.items = InboundOrder.objects.all()
        params.result = Mock(return_value=[])

        with patch(
            "apps.operations.layers.applications.inbound_service.DatatableSearch.retrieve_orders"
        ) as mock_retrieve:
            result = service.get_inbound_orders(params)

            assert result == params.result.return_value
            mock_retrieve.assert_called_once_with(params)

    def test_get_inbound_orders_failure(self, service):
        """Test it retrieving inbound orders with error."""
        params = Mock()
        params.items = Mock()
        params.items.annotate = Mock(side_effect=Exception("Database error"))

        result = service.get_inbound_orders(params)

        assert result == []

    # ============ TESTS: save_inbound_order ============

    def test_save_inbound_order_success(self, service, supplier, supply, user, batch):
        """Test creating a new inbound order successfully."""
        payload = {
            "order_type": InventoryOrder.OrderType.INBOUND,
            "motive": "Test purchase",
            "status": InventoryOrder.StatusType.SENT,
            "supplier": supplier.id,
            "scheduled_date": date.today() + timedelta(days=7),
            "observations": "Test observations",
        }
        line_details = [
            {
                "supply_id": supply.id,
                "batch_number": batch.batch_number,
                "expiry_date": batch.expiry_date,
                "quantity_requested": 10,
                "unit_cost": Decimal("10.00"),
                "observations": "",
            }
        ]

        with patch(
            "apps.operations.layers.applications.inbound_service.BatchAppService"
        ) as mock_service:
            mock_service.return_value.register_batch.return_value = batch
            result = service.save_inbound_order(InboundOrder(), payload, line_details, user)

            assert result is not None
            assert result.order_number.startswith("IN-")
            assert result.motive == "Test purchase"
            assert result.supplier.id == supplier.id
            assert result.details.count() == 1

            detail = result.details.first()
            assert detail.supply.id == supply.id
            assert detail.quantity_requested == 10

    def test_save_inbound_order_missing_required_fields(self, service, supplier):
        """Test creating order with missing required fields."""
        payload = {
            "order_type": InventoryOrder.OrderType.INBOUND,
            "status": InventoryOrder.StatusType.SENT,
        }
        line_details = []

        with pytest.raises(ValidationError) as excinfo:
            service.save_inbound_order(InboundOrder(), payload, line_details, None)

        assert "motive" in str(excinfo.value) or "supplier" in str(excinfo.value)

    def test_save_inbound_order_no_line_details(self, service, supplier, user):
        """Test creating order without line details."""
        payload = {
            "order_type": InventoryOrder.OrderType.INBOUND,
            "motive": "Test purchase",
            "status": InventoryOrder.StatusType.SENT,
            "supplier": supplier.id,
            "scheduled_date": date.today() + timedelta(days=7),
        }

        with pytest.raises(ValidationError) as excinfo:
            service.save_inbound_order(InboundOrder(), payload, [], user)

        assert "At least one line detail is required" in str(excinfo.value)

    def test_save_inbound_order_missing_line_required_fields(self, service, supplier, user):
        """Test creating order with missing required fields in line details."""
        payload = {
            "order_type": InventoryOrder.OrderType.INBOUND,
            "motive": "Test purchase",
            "status": InventoryOrder.StatusType.SENT,
            "supplier": supplier.id,
            "scheduled_date": date.today() + timedelta(days=7),
        }
        line_details = [
            {"batch_number": "LOTE-001", "expiry_date": date.today() + timedelta(days=365)}
        ]

        with pytest.raises(ValidationError) as excinfo:
            service.save_inbound_order(InboundOrder(), payload, line_details, user)

        assert "Missing required fields" in str(excinfo.value)

    def test_save_inbound_order_without_user(self, service, supplier, supply, batch):
        """Test creating order without a user (should use 'system' as created_by)."""
        payload = {
            "order_type": InventoryOrder.OrderType.INBOUND,
            "motive": "Test purchase",
            "status": InventoryOrder.StatusType.SENT,
            "supplier": supplier.id,
            "scheduled_date": date.today() + timedelta(days=7),
        }
        line_details = [
            {
                "supply_id": supply.id,
                "batch_number": batch.batch_number,
                "expiry_date": batch.expiry_date,
                "quantity_requested": 10,
                "unit_cost": Decimal("10.00"),
                "observations": "",
            }
        ]

        with patch(
            "apps.operations.layers.applications.inbound_service.BatchAppService"
        ) as mock_service:
            mock_service.return_value.register_batch.return_value = batch
            result = service.save_inbound_order(InboundOrder(), payload, line_details, None)

            assert result.created_by == "system"

    # ============ TESTS: update_inbound_order ============

    def test_update_inbound_order_success(self, service, inbound_order, supply, batch):
        """Test updating an existing inbound order."""
        payload = {"status": InventoryOrder.StatusType.COMPLETED}
        details_payload = [
            {
                "order_type": InventoryOrder.OrderType.INBOUND,
                "supply_id": supply.id,
                "batch_number": "LOTE-001",
                "expiry_date": date.today() + timedelta(days=365),
                "quantity_requested": 15,
                "quantity_fulfilled": 15,
                "unit_cost": Decimal("12.00"),
                "observations": "Updated observations",
            }
        ]

        # Add existing detail to order
        OrderDetail.objects.create(
            inventory_order=inbound_order,
            supply=supply,
            batch=batch,
            quantity_requested=10,
            quantity_fulfilled=0,
            unit_cost=Decimal("10.00"),
        )

        result = service.update_inbound_order(inbound_order, payload, details_payload)

        assert result.status == InventoryOrder.StatusType.COMPLETED
        assert result.details.count() == 1

        updated_detail = result.details.first()
        assert updated_detail.quantity_requested == 15
        assert updated_detail.quantity_fulfilled == 15

    def test_update_inbound_order_delete_detail(self, service, inbound_order, supply, batch):
        """Test updating order removes details not in the payload."""
        payload = {"status": InventoryOrder.StatusType.SENT}

        # Create existing detail
        OrderDetail.objects.create(
            inventory_order=inbound_order,
            supply=supply,
            batch=batch,
            quantity_requested=10,
            quantity_fulfilled=0,
            unit_cost=Decimal("10.00"),
        )

        assert inbound_order.details.count() == 1

        # Update with empty details
        result = service.update_inbound_order(inbound_order, payload, [])

        assert result.details.count() == 0

    def test_update_inbound_order_with_zero_quantity(self, service, inbound_order, supply, batch):
        """Test updating order with zero quantity (should skip)."""
        payload = {"status": InventoryOrder.StatusType.SENT}
        details_payload = [
            {
                "supply_id": supply.id,
                "batch_number": "LOTE-001",
                "expiry_date": date.today() + timedelta(days=365),
                "quantity_requested": 10,
                "quantity_fulfilled": 0,
                "unit_cost": Decimal("10.00"),
                "observations": "",
            }
        ]

        # Create existing detail
        OrderDetail.objects.create(
            inventory_order=inbound_order,
            supply=supply,
            batch=batch,
            quantity_requested=10,
            quantity_fulfilled=0,
            unit_cost=Decimal("10.00"),
        )

        result = service.update_inbound_order(inbound_order, payload, details_payload)
        # Detail with 0 should not be processed
        assert result.details.count() == 0

    # ============ TESTS: complete_purchase_order ============

    def test_complete_purchase_order_success(self, service, inbound_order, supply, batch):
        """Test completing a purchase order."""
        # Create detail with batch
        detail = OrderDetail.objects.create(
            inventory_order=inbound_order,
            supply=supply,
            batch=batch,
            quantity_requested=10,
            quantity_fulfilled=0,
            unit_cost=Decimal("10.00"),
        )

        # Mock _build_movement
        service._build_movement = Mock()

        result = service.complete_purchase_order(inbound_order)

        assert result.status == InboundOrder.StatusType.COMPLETED
        assert result.received_date is not None

        detail.refresh_from_db()
        assert detail.quantity_fulfilled == detail.quantity_requested

        batch.refresh_from_db()
        assert batch.current_quantity == detail.quantity_requested
        assert batch.status == Batch.BatchStatus.ACTIVE

        service._build_movement.assert_called_once()

    def test_complete_purchase_order_already_completed(self, service, inbound_order):
        """Test completing an already completed order."""
        inbound_order.status = InboundOrder.StatusType.COMPLETED
        inbound_order.save()

        service._build_movement = Mock()

        result = service.complete_purchase_order(inbound_order)

        # Should return without changes
        assert result.status == InboundOrder.StatusType.COMPLETED
        service._build_movement.assert_not_called()

    def test_complete_purchase_order_no_details(self, service, inbound_order):
        """Test completing order with no details."""
        service._build_movement = Mock()

        result = service.complete_purchase_order(inbound_order)

        assert result.status == InboundOrder.StatusType.COMPLETED
        service._build_movement.assert_not_called()

    # ============ TESTS: cancel_purchase_order ============

    def test_cancel_purchase_order_success(self, service, inbound_order, supply, batch):
        """Test cancelling a purchase order."""
        # Create detail with batch
        OrderDetail.objects.create(
            inventory_order=inbound_order,
            supply=supply,
            batch=batch,
            quantity_requested=10,
            quantity_fulfilled=0,
            unit_cost=Decimal("10.00"),
        )

        result = service.cancel_purchase_order(inbound_order)

        assert result.status == InboundOrder.StatusType.CANCELLED

        batch.refresh_from_db()
        assert batch.current_quantity == 0
        assert batch.status == Batch.BatchStatus.DISCARDED

    def test_cancel_purchase_order_already_cancelled(self, service, inbound_order):
        """Test cancelling an already canceled order."""
        inbound_order.status = InboundOrder.StatusType.CANCELLED
        inbound_order.save()

        service._build_movement = Mock()

        result = service.cancel_purchase_order(inbound_order)

        assert result.status == InboundOrder.StatusType.CANCELLED
        service._build_movement.assert_not_called()

    def test_cancel_purchase_order_no_details(self, service, inbound_order):
        """Test cancelling order with no details."""
        result = service.cancel_purchase_order(inbound_order)

        assert result.status == InboundOrder.StatusType.CANCELLED
        assert result.details.count() == 0

    # ============ TESTS: _build_movement ============

    def test_build_movement_inbound(self, service, order_payload, batch, line_details, user):
        """Test it building inbound movement."""
        order = service.save_inbound_order(InboundOrder(), order_payload, line_details, user)
        service._build_movement(batch, order.id, movement_type=InventoryMovement.Type.INBOUND)

        movement = InventoryMovement.objects.filter(batch=batch).first()
        assert movement is not None
        assert movement.movement_type == InventoryMovement.Type.INBOUND
        assert movement.status == InventoryMovement.MovementStatusChoices.COMPLETED

    def test_build_movement_with_custom_quantity(self, service, order_payload, line_details, batch):
        """Test building movement with custom quantity."""
        custom_quantity = 5
        order = service.save_inbound_order(InboundOrder(), order_payload, line_details, user=None)
        service._build_movement(
            batch, order.id, movement_type=InventoryMovement.Type.INBOUND, quantity=custom_quantity
        )

        movement = InventoryMovement.objects.filter(batch=batch).first()
        assert movement is not None
        assert movement.quantity == custom_quantity

    # ============ TESTS: _get_or_create_batch ============

    def test_get_or_create_batch_exists(self, service, inbound_order, supply, batch):
        """Test getting an existing batch."""
        result = service._get_or_create_batch(
            inbound_order,
            {
                "supply_id": supply.id,
                "batch_number": batch.batch_number,
                "expiry_date": date.today() + timedelta(days=365),
                "unit_cost": Decimal("10.00"),
                "quantity_requested": 10,
            },
            10,
        )

        assert result.id == batch.id
        assert result.batch_number == batch.batch_number

    def test_get_or_create_batch_new(self, service, inbound_order, supply):
        """Test creating a new batch."""
        batch_data = {
            "supply_id": supply.id,
            "batch_number": "LOTE-NEW",
            "expiry_date": date.today() + timedelta(days=365),
            "unit_cost": Decimal("15.00"),
            "quantity_requested": 20,
        }

        result = service._get_or_create_batch(inbound_order, batch_data, 20)

        assert result.id is not None
        assert result.batch_number == "LOTE-NEW"
        assert result.current_quantity == 20
        assert result.initial_quantity == 20
        assert result.unit_cost == Decimal("15.00")
        assert result.supply.id == supply.id

    # ============ TESTS: _validate_line_detail ============

    def test_validate_line_detail_success(self, service):
        """Test validating line detail with all required fields."""
        line = {"supply_id": 1, "quantity_requested": 10}
        # Should not raise exception
        service._validate_line_detail(line)

    def test_validate_line_detail_missing_fields(self, service):
        """Test validating line detail with missing required fields."""
        line = {"batch_number": "LOTE-001"}

        with pytest.raises(ValidationError) as excinfo:
            service._validate_line_detail(line)

        assert "Missing required fields" in str(excinfo.value)
        assert "supply_id" in str(excinfo.value)
        assert "quantity_requested" in str(excinfo.value)

    # ============ TESTS: _build_order_from_payload ============

    def test_build_order_from_payload_success(self, service, supplier):
        """Test building order from payload."""
        builder = Mock()
        payload = {
            "order_type": InventoryOrder.OrderType.INBOUND,
            "motive": "Test order",
            "status": InventoryOrder.StatusType.SENT,
            "supplier": supplier.id,
            "scheduled_date": date.today() + timedelta(days=7),
            "observations": "Test observations",
            "received_date": date.today(),
        }

        service._build_order_from_payload(builder, payload)

        builder.set_order_type.assert_called_with(payload["order_type"])
        builder.set_motive.assert_called_with(payload["motive"])
        builder.set_status.assert_called_with(payload["status"])
        builder.set_supplier.assert_called_with(payload["supplier"])
        builder.set_scheduled_date.assert_called_with(payload["scheduled_date"])
        builder.set_observations.assert_called_with(payload["observations"])
        builder.set_received_date.assert_called_with(payload["received_date"])

    def test_build_order_from_payload_missing_required(self, service):
        """Test building order with missing required fields."""
        builder = Mock()
        payload = {"order_type": InventoryOrder.OrderType.INBOUND}

        with pytest.raises(ValidationError) as excinfo:
            service._build_order_from_payload(builder, payload)

        assert "motive" in str(excinfo.value)
