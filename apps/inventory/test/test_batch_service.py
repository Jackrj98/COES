# apps/inventory/test/test_batch_service.py

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.catalogs.models import Catalog, CatalogItem
from apps.inventory.layers.applications import BatchAppService
from apps.inventory.models import Batch, Supply


@pytest.fixture
def service():
    return BatchAppService()


@pytest.fixture
def category(db):
    """Create a category catalog item for supplies."""
    catalog, _ = Catalog.objects.get_or_create(
        code="SUPPLY_CATEGORY",
        defaults={"name": "Supply Categories", "description": "Categories for supplies"},
    )

    category_item = CatalogItem.objects.create(
        catalog=catalog, code="CAT-MEDICINES", name="Medicines", priority=1, is_active=True
    )
    return category_item


@pytest.fixture
def unit_of_measure(db):
    """Create a unit of measure catalog item."""
    catalog, _ = Catalog.objects.get_or_create(
        code="UNIT_OF_MEASURE",
        defaults={"name": "Units of Measure", "description": "Units of measure for supplies"},
    )

    unit = CatalogItem.objects.create(
        catalog=catalog, code="UOM-UND", name="Unit", extra="u", priority=1, is_active=True
    )
    return unit


@pytest.fixture
def supply(db, category, unit_of_measure):
    """Create a supply with the required category and unit of measure."""
    return Supply.objects.create(
        name="Test Supply",
        code="SUP001",
        description="Test Description",
        category=category,
        unit_of_measure=unit_of_measure,
        is_active=True,
        stock_min=10,
    )


@pytest.fixture
def valid_batch_payload(supply):
    return {
        "batch_number": "BATCH-001",
        "expiry_date": timezone.now().date() + timedelta(days=365),
        "initial_quantity": 100,
        "current_quantity": 100,
        "unit_cost": Decimal("50.00"),
        "status": Batch.BatchStatus.ACTIVE,
        "is_active": True,
        "supply_id": supply.id,
    }


@pytest.fixture
def existing_batch(service, valid_batch_payload):
    return service.register_batch(valid_batch_payload)


# ---------------------------------------------------------------------------
# Test Register Batch
# ---------------------------------------------------------------------------


class TestRegisterBatch:
    @pytest.mark.django_db
    def test_register_success(self, service, valid_batch_payload):
        batch = service.register_batch(valid_batch_payload)

        assert batch.id is not None
        assert batch.batch_number == "BATCH-001"
        assert batch.supply_id == valid_batch_payload["supply_id"]
        assert batch.initial_quantity == 100
        assert batch.current_quantity == 100
        assert batch.unit_cost == Decimal("50.00")
        assert batch.status == Batch.BatchStatus.ACTIVE
        assert batch.is_active is True

    @pytest.mark.django_db
    def test_register_duplicate_batch_number_raises_error(self, service, valid_batch_payload):
        service.register_batch(valid_batch_payload)

        with pytest.raises(Exception):
            service.register_batch(valid_batch_payload)

    @pytest.mark.django_db
    def test_register_with_expired_date(self, service, valid_batch_payload):
        valid_batch_payload["expiry_date"] = timezone.now().date() - timedelta(days=1)
        valid_batch_payload["batch_number"] = "BTH-EXPIRED"

        batch = service.register_batch(valid_batch_payload)

        assert batch.expiry_date < timezone.now().date()
        assert batch.status == Batch.BatchStatus.EXPIRED

    @pytest.mark.django_db
    def test_update_to_zero_quantity_marks_depleted(self, service, existing_batch):
        """Test that updating quantity to zero marks batch as depleted."""
        # El servicio actualiza automáticamente el status cuando quantity es 0
        update_payload = {
            "batch_number": existing_batch.batch_number,
            "expiry_date": existing_batch.expiry_date,
            "initial_quantity": existing_batch.initial_quantity,
            "current_quantity": 0,
            "unit_cost": existing_batch.unit_cost,
            "supply_id": existing_batch.supply_id,
            "is_active": True,
            # No incluir status, el servicio lo manejará automáticamente
        }

        updated_batch = service.update_batch(existing_batch, update_payload)

        assert updated_batch.current_quantity == 0
        assert updated_batch.status == Batch.BatchStatus.DEPLETED

    @pytest.mark.django_db
    def test_update_to_zero_quantity_manually_set_depleted(self, service, existing_batch):
        """Test manually setting status to depleted when quantity is zero."""
        update_payload = {
            "batch_number": existing_batch.batch_number,
            "expiry_date": existing_batch.expiry_date,
            "initial_quantity": existing_batch.initial_quantity,
            "current_quantity": 0,
            "unit_cost": existing_batch.unit_cost,
            "status": Batch.BatchStatus.DEPLETED,
            "supply_id": existing_batch.supply_id,
            "is_active": True,
        }

        updated_batch = service.update_batch(existing_batch, update_payload)

        assert updated_batch.current_quantity == 0
        assert updated_batch.status == Batch.BatchStatus.DEPLETED


# ---------------------------------------------------------------------------
# Test Update Batch
# ---------------------------------------------------------------------------


class TestUpdateBatch:
    @pytest.mark.django_db
    def test_update_success(self, service, valid_batch_payload):
        batch = service.register_batch(valid_batch_payload)

        update_payload = {
            "batch_number": "BATCH-002",
            "expiry_date": valid_batch_payload["expiry_date"],
            "initial_quantity": valid_batch_payload["initial_quantity"],
            "current_quantity": 50,
            "unit_cost": Decimal("45.00"),
            "status": valid_batch_payload["status"],
            "supply_id": valid_batch_payload["supply_id"],
            "is_active": True,
        }

        updated = service.update_batch(batch, update_payload)

        assert updated.batch_number == "BATCH-002"
        assert updated.current_quantity == 50
        assert updated.unit_cost == Decimal("45.00")
        assert updated.id == batch.id

    @pytest.mark.django_db
    def test_update_batch_number_to_duplicate_raises_error(self, service, valid_batch_payload):
        service.register_batch(valid_batch_payload)

        second_payload = valid_batch_payload.copy()
        second_payload["batch_number"] = "BATCH-002"
        batch2 = service.register_batch(second_payload)

        update_payload = valid_batch_payload.copy()
        update_payload["batch_number"] = "BATCH-001"

        with pytest.raises(Exception):
            service.update_batch(batch2, update_payload)

    @pytest.mark.django_db
    def test_update_none_instance_raises_error(self, service, valid_batch_payload):
        with pytest.raises(ValueError, match="Batch instance is required"):
            service.update_batch(None, valid_batch_payload)

    @pytest.mark.django_db
    def test_update_partial_fields(self, service, valid_batch_payload):
        batch = service.register_batch(valid_batch_payload)

        update_payload = {
            "batch_number": "BATCH-PARTIAL",
            "current_quantity": 75,
            "expiry_date": valid_batch_payload["expiry_date"],
            "unit_cost": Decimal("55.00"),
            "supply_id": valid_batch_payload["supply_id"],
            "is_active": True,
        }

        updated = service.update_batch(batch, update_payload)

        assert updated.batch_number == "BATCH-PARTIAL"
        assert updated.current_quantity == 75
        assert updated.unit_cost == Decimal("55.00")


# ---------------------------------------------------------------------------
# Test Update Batch Stock
# ---------------------------------------------------------------------------


class TestUpdateBatchStock:
    @pytest.mark.django_db
    def test_update_stock_success(self, service, existing_batch):
        updated = service.update_batch_stock(existing_batch, 75)

        assert updated.current_quantity == 75
        assert updated.id == existing_batch.id

    @pytest.mark.django_db
    def test_update_stock_to_zero_marks_depleted(self, service, existing_batch):
        updated = service.update_batch_stock(existing_batch, 0)

        assert updated.current_quantity == 0
        assert updated.status == Batch.BatchStatus.DEPLETED

    @pytest.mark.django_db
    def test_update_stock_negative_raises_error(self, service, existing_batch):
        with pytest.raises(Exception):
            service.update_batch_stock(existing_batch, -10)


# ---------------------------------------------------------------------------
# Test Retrieve Methods
# ---------------------------------------------------------------------------


class TestRetrieveBatches:
    @pytest.mark.django_db
    def test_retrieve_batches_success(self, service, valid_batch_payload, supply):
        service.register_batch(valid_batch_payload)

        class MockParams:
            def __init__(self):
                self.items = Batch.objects.filter(supply=supply)
                self.start = 0
                self.length = 10

            def result(self, data):
                return {"data": data, "recordsTotal": self.items.count()}

        params = MockParams()
        result = service.retrieve_batches(params, supply.external_id)

        assert result is not None
        assert "data" in result

    @pytest.mark.django_db
    def test_retrieve_batches_empty(self, service, supply):
        class MockParams:
            def __init__(self):
                self.items = Batch.objects.none()
                self.start = 0
                self.length = 10

            def result(self, data):
                return {"data": data, "recordsTotal": 0}

        params = MockParams()
        result = service.retrieve_batches(params, supply.external_id)

        assert result["data"] == []
        assert result["recordsTotal"] == 0


class TestRetrieveStockTotal:
    @pytest.mark.django_db
    def test_retrieve_stock_total_success(self, service, valid_batch_payload, supply):
        service.register_batch(valid_batch_payload)

        second_payload = valid_batch_payload.copy()
        second_payload["batch_number"] = "BATCH-002"
        second_payload["current_quantity"] = 50

        service.register_batch(second_payload)

        total = service.retrieve_stock_total(supply.external_id)

        assert total == 150

    @pytest.mark.django_db
    def test_retrieve_stock_total_no_batches(self, service, supply):
        total = service.retrieve_stock_total(supply.external_id)

        assert total == 0


class TestRetrieveByExpiryDate:
    @pytest.mark.django_db
    def test_retrieve_by_expiry_date_success(self, service, valid_batch_payload, supply):
        date1 = timezone.now().date() + timedelta(days=30)
        date2 = timezone.now().date() + timedelta(days=60)
        date3 = timezone.now().date() + timedelta(days=90)

        pay1 = valid_batch_payload.copy()
        pay1["batch_number"] = "BATCH-D1"
        pay1["expiry_date"] = date1
        service.register_batch(pay1)

        pay2 = valid_batch_payload.copy()
        pay2["batch_number"] = "BATCH-D2"
        pay2["expiry_date"] = date2
        service.register_batch(pay2)

        pay3 = valid_batch_payload.copy()
        pay3["batch_number"] = "BATCH-D3"
        pay3["expiry_date"] = date3
        service.register_batch(pay3)

        result = service.retrieve_by_expiry_date(supply.id)

        assert len(result) == 3
        assert result[0].expiry_date == date1
        assert result[1].expiry_date == date2
        assert result[2].expiry_date == date3

    @pytest.mark.django_db
    def test_retrieve_by_expiry_date_only_active(self, service, valid_batch_payload, supply):
        b1 = valid_batch_payload.copy()
        b1["batch_number"] = "BATCH-ACTIVE"
        service.register_batch(b1)

        b2 = valid_batch_payload.copy()
        b2["batch_number"] = "BATCH-INACTIVE"
        b2["is_active"] = False
        service.register_batch(b2)

        b3 = valid_batch_payload.copy()
        b3["batch_number"] = "BATCH-EMPTY"
        b3["current_quantity"] = 0
        service.register_batch(b3)

        result = service.retrieve_by_expiry_date(supply.id)

        assert len(result) == 1
        assert result[0].batch_number == "BATCH-ACTIVE"


# ---------------------------------------------------------------------------
# Edge Cases and Error Handling
# ---------------------------------------------------------------------------


class TestBatchEdgeCases:
    @pytest.mark.django_db
    def test_batch_with_future_expiry_date(self, service, valid_batch_payload):
        future_date = timezone.now().date() + timedelta(days=730)
        b1 = valid_batch_payload.copy()
        b1["batch_number"] = "BATCH-FUTURE"
        b1["expiry_date"] = future_date

        batch = service.register_batch(b1)

        assert batch.expiry_date == future_date
        assert batch.status == Batch.BatchStatus.ACTIVE

    @pytest.mark.django_db
    def test_batch_with_today_expiry_date(self, service, valid_batch_payload):
        today = timezone.now().date()
        b1 = valid_batch_payload.copy()
        b1["batch_number"] = "BATCH-TODAY"
        b1["expiry_date"] = today

        batch = service.register_batch(b1)

        assert batch.expiry_date == today

    @pytest.mark.django_db
    def test_multiple_batches_same_supply(self, service, valid_batch_payload, supply):
        p1 = valid_batch_payload.copy()
        p1["batch_number"] = "BATCH-M1"
        batch1 = service.register_batch(p1)

        p2 = valid_batch_payload.copy()
        p2["batch_number"] = "BATCH-M2"
        batch2 = service.register_batch(p2)

        assert Batch.objects.filter(supply=supply).count() == 2
        assert batch1.supply_id == batch2.supply_id
