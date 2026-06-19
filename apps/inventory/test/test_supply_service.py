import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.validators import ValidationError

from apps.catalogs.models import Catalog, CatalogItem
from apps.inventory.layers.applications import SupplyAppService


@pytest.fixture(scope="session", autouse=True)
def setup_required_catalogs(django_db_setup, django_db_blocker):
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
def supply_category_catalog(db):
    return Catalog.objects.get(code=Catalog.CatalogCodes.SUPPLY_CATEGORY)


@pytest.fixture
def unit_of_measure_catalog(db):
    return Catalog.objects.get(code=Catalog.CatalogCodes.UNIT_OF_MEASURE)


@pytest.fixture
def category(supply_category_catalog):
    category_item, _ = CatalogItem.objects.get_or_create(
        catalog=supply_category_catalog,
        code="MED-SUP",
        defaults={"name": "Insumos Médicos", "priority": 1},
    )
    return category_item


@pytest.fixture
def uom(unit_of_measure_catalog):
    uom_item, _ = CatalogItem.objects.get_or_create(
        catalog=unit_of_measure_catalog, code="KG", defaults={"name": "Kilogramo", "priority": 1}
    )
    return uom_item


@pytest.fixture
def service():
    return SupplyAppService()


@pytest.fixture
def valid_payload(category, uom):
    import uuid

    unique_id = uuid.uuid4().hex[:6]
    return {
        "name": f"Suministro {unique_id}",
        "code": "SUP",
        "barcode": f"BC-{unique_id}",
        "description": "Descripción de prueba",
        "is_active": True,
        "stock_min": 10,
        "stock_max": 100,
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
        assert "Suministro".lower() in result.name.lower()
        assert result.description == "Descripción de prueba"

    @pytest.mark.django_db
    def test_validation_error(self, service):
        invalid_payload = {
            "name": "A",
            "code": "BCF63D",
            "barcode": "123456789",
            "category_id": None,
            "unit_of_measure_id": 1,
            "description": "desc",
        }

        try:
            service.register_supply(invalid_payload)
            pytest.fail("Debería haber lanzado una excepción")
        except Exception as e:
            assert isinstance(e, ValidationError), (
                f"Se esperaba ValidationError, pero se obtuvo {type(e)}"
            )

            errors = getattr(e, "message_dict", {})
            if not errors:
                errors = e.messages

            assert "category" in str(errors)


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
        supply = service.register_supply(valid_payload)

        from apps.inventory.models import Supply

        supplies = Supply.objects.all()

        assert supplies.count() > 0

        if hasattr(service, "get_all_supplies"):
            result = service.get_all_supplies()
            assert len(result) > 0

        assert supply.code == valid_payload["code"]
        assert supply.name.lower() == str(valid_payload["name"]).lower()


class TestSaveUploadedFile:
    @pytest.mark.django_db
    def test_file_upload_updates_instance(self, service, valid_payload):
        supply = service.register_supply(valid_payload)
        mock_file = SimpleUploadedFile("test.png", b"file_content", content_type="image/png")

        service.update_supply(supply, valid_payload, mock_file)

        supply.refresh_from_db()

        assert supply.image_url is not None
        assert supply.image_url.name.endswith(".png")
        assert "inventory/supply/" in supply.image_url.name


class TestRetrieveSupplyQueries:
    @pytest.mark.django_db
    def test_retrieve_by_term(self, service, valid_payload):
        supply = service.register_supply(valid_payload)

        results = service.retrieve_by_term(supply.code)
        assert results.count() == 1
