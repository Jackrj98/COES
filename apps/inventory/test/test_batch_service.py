from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from apps.inventory.layers.applications import BatchAppService
from apps.inventory.models import Supply


@pytest.fixture
def service():
    return BatchAppService()


@pytest.fixture
def supply(db):
    return Supply.objects.create(name="Test Supply", code="SUP001")


@pytest.fixture
def valid_batch_payload(supply):
    return {
        "number": "BATCH-001",
        "due_date": date.today(),
        "stock": 10,
        "purchase_unit_cost": 50.0,
        "status": 1,
        "supply_id": supply.id,
    }


# ---------------------------------------------------------------------------
# Test Register Batch
# ---------------------------------------------------------------------------


class TestRegisterBatch:
    @pytest.mark.django_db
    def test_register_success(self, service, valid_batch_payload):
        batch = service.register_batch(valid_batch_payload)
        assert batch.id is not None
        assert batch.number == "BATCH-001"
        assert batch.supply_id == valid_batch_payload["supply_id"]

    @pytest.mark.django_db
    def test_register_invalid_due_date(self, service, valid_batch_payload):
        invalid_payload = {**valid_batch_payload, "due_date": date.today() - timedelta(days=1)}

        with pytest.raises(ValidationError):
            service.register_batch(invalid_payload)

    @pytest.mark.django_db
    def test_register_negative_stock(self, service, valid_batch_payload):
        invalid_payload = {**valid_batch_payload, "stock": -5}

        with pytest.raises(ValidationError):
            service.register_batch(invalid_payload)


# ---------------------------------------------------------------------------
# Test Update Batch
# ---------------------------------------------------------------------------


class TestUpdateBatch:
    @pytest.mark.django_db
    def test_update_success(self, service, valid_batch_payload):
        batch = service.register_batch(valid_batch_payload)
        update_data = {**valid_batch_payload, "stock": 200, "number": "BATCH-002"}
        updated = service.update_batch(batch, update_data)

        assert updated.stock == 200
        assert updated.number == "BATCH-002"

    @pytest.mark.django_db
    def test_update_none_instance_raises_error(self, service, valid_batch_payload):
        with pytest.raises(ValueError, match="Batch instance is required"):
            service.update_batch(None, valid_batch_payload)
