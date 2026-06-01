from unittest.mock import MagicMock

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from pydantic import ValidationError

from apps.catalogs.models import Catalog, CatalogItem
from apps.inventory.layers.applications import SupplyAppService


@pytest.fixture
def supply_category_catalog(db):
    return Catalog.objects.create(code=Catalog.CatalogCodes.SUPPLY_CATEGORY, name="Categorias")


@pytest.fixture
def uom_catalog(db):
    return Catalog.objects.create(code=Catalog.CatalogCodes.UNIT_OF_MEASURE, name="Unidades")


@pytest.fixture
def category(supply_category_catalog):
    return CatalogItem.objects.create(
        catalog=supply_category_catalog, name="Test Cat", code="CAT01"
    )


@pytest.fixture
def uom(uom_catalog):
    return CatalogItem.objects.create(catalog=uom_catalog, name="Kg", code="KG")


@pytest.fixture
def service():
    return SupplyAppService()


@pytest.fixture
def valid_payload(category, uom):
    return {
        "name": "Suministro Test",
        "code": "SUP001",
        "description": "Descripción de prueba",
        "is_active": True,
        "stock_min": 10,
        "category_id": category.id,
        "unit_of_measure_id": uom.id,
    }


# ---------------------------------------------------------------------------
# Test Classes
# ---------------------------------------------------------------------------


class TestRegisterSupply:
    @pytest.mark.django_db
    def test_success(self, service, valid_payload):
        result = service.register_supply(valid_payload)
        assert result.id is not None
        assert len(result.code) > 0
        assert result.code.isalnum()

    @pytest.mark.django_db
    def test_validation_error(self, service):
        invalid_payload = {"name": "A"}
        with pytest.raises(ValidationError):
            service.register_supply(invalid_payload)


class TestUpdateSupply:
    @pytest.mark.django_db
    def test_success(self, service, valid_payload):
        supply = service.register_supply(valid_payload)
        update_data = {**valid_payload, "name": "Nombre Actualizado"}

        updated = service.update_supply(supply, update_data)
        assert updated.name.lower() == "nombre actualizado"
        assert updated.code == supply.code

    @pytest.mark.django_db
    def test_raises_error_when_instance_is_none(self, service, valid_payload):
        with pytest.raises(ValueError, match="Supply instance is required"):
            service.update_supply(None, valid_payload)


class TestRetrieveSuppliers:
    @pytest.mark.django_db
    def test_returns_data_in_datatable_format(self, service, valid_payload):
        service.register_supply(valid_payload)

        params = MagicMock()
        params.get.return_value = "2026-06-01"

        params.result.return_value = [{"name": "Suministro Test"}]
        result = service.retrieve_suppliers(params)
        assert len(result) > 0


class TestSaveUploadedFile:
    @pytest.mark.django_db
    def test_file_upload_updates_instance(self, service, valid_payload):
        supply = service.register_supply(valid_payload)
        mock_file = SimpleUploadedFile("test.png", b"file_content", content_type="image/png")

        service._save_uploaded_file(mock_file, supply)

        supply.refresh_from_db()

        assert supply.image_url is not None
        assert supply.image_url.name.endswith(".png")
        assert "inventory/supply/" in supply.image_url.name
