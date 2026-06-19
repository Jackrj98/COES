import pytest

from apps.catalogs.layers.applications.catalog_item_service import CatalogItemAppService
from apps.catalogs.models import Catalog, CatalogItem

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def service():
    return CatalogItemAppService()


@pytest.fixture
def catalog():
    return Catalog.objects.create(name="Test Catalog", code="CAT001", priority=1, is_active=True)


@pytest.fixture
def valid_payload(catalog):
    return {
        "name": "Test Item",
        "code": "ITEM001",
        "description": "Item description",
        "priority": 1,
        "is_active": True,
        "extra": "lb",
        "catalog_id": catalog.id,
    }


@pytest.fixture
def catalog_item(catalog, valid_payload):
    return CatalogItem.objects.create(
        name=valid_payload["name"],
        code=valid_payload["code"],
        description=valid_payload["description"],
        priority=valid_payload["priority"],
        is_active=valid_payload["is_active"],
        catalog=catalog,
        extra=valid_payload["extra"],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCatalogItemAppService:
    """Grouped tests for CatalogItemAppService."""

    def test_retrieve_catalog_by_external_success(self, service, catalog):
        """Retrieve catalog by external reference."""
        result = service.retrieve_catalog_by_external(str(catalog.external_id))
        assert result.id == catalog.id

    def test_retrieve_catalog_by_external_not_found(self, service):
        """Error when catalog does not exist - use a valid but non-existent UUID."""
        import uuid

        non_existent_uuid = str(uuid.uuid4())  # Valid UUID but does not exist
        with pytest.raises(ValueError, match="Catalog with the provided reference does not exist"):
            service.retrieve_catalog_by_external(non_existent_uuid)

    def test_retrieve_by_code_success(self, service, catalog, catalog_item):
        """Retrieve item by code."""
        result = service.retrieve_by_code("ITEM001", catalog.code)
        assert result.code == "ITEM001"

    def test_retrieve_by_code_not_found(self, service, catalog):
        """Item does not exist."""
        assert service.retrieve_by_code("NONEXISTENT", catalog.code) is None

    def test_retrieve_by_code_missing_params(self, service):
        """Error when parameters are missing."""
        with pytest.raises(ValueError, match="Code and catalog code are required"):
            service.retrieve_by_code("", "CAT001")

    def test_retrieve_catalog_items_success(self, service, catalog, catalog_item):
        """List items from a catalog."""
        result = service.retrieve_catalog_items(catalog.code)
        assert len(result) == 1
        assert result[0].code == "ITEM001"

    def test_retrieve_catalog_items_empty(self, service, catalog):
        """List items from a catalog with no items."""
        result = service.retrieve_catalog_items(catalog.code)
        assert len(result) == 0

    def test_retrieve_by_priority_success(self, service, catalog, catalog_item):
        """Retrieve item by priority."""
        result = service.retrieve_by_priority(catalog.code, 1)
        assert result.priority == 1

    def test_generate_next_priority(self, service, catalog, valid_payload):
        """Generate next priority."""
        assert service.generate_next_priority(catalog.code) == 1

        service.register_item({**valid_payload, "priority": 5}, str(catalog.external_id))
        assert service.generate_next_priority(catalog.code) == 6

    def test_register_item_success(self, service, catalog, valid_payload):
        """Register item successfully."""
        result = service.register_item(valid_payload, str(catalog.external_id))

        assert result.code == "ITEM001"
        assert result.catalog.id == catalog.id
        assert CatalogItem.objects.filter(code="ITEM001").exists()

    def test_register_item_duplicate_code(self, service, catalog, valid_payload):
        """Error when registering a duplicate code."""
        service.register_item(valid_payload, str(catalog.external_id))

        with pytest.raises(Exception, match="already exists"):
            service.register_item(valid_payload, str(catalog.external_id))

    def test_register_item_catalog_not_found(self, service, valid_payload):
        """Error when catalog does not exist - use a valid but non-existent UUID."""
        import uuid

        non_existent_uuid = str(uuid.uuid4())  # Valid UUID but does not exist
        with pytest.raises(ValueError, match="Catalog with the provided reference does not exist"):
            service.register_item(valid_payload, non_existent_uuid)

    def test_update_item_success(self, service, catalog, catalog_item, valid_payload):
        """Update item successfully."""
        update_data = {**valid_payload, "name": "Updated", "priority": 10}
        updated = service.update_item(catalog_item, update_data, str(catalog.external_id))

        assert updated.name == "Updated"
        assert updated.priority == 10

    def test_update_item_none_instance(self, service, catalog, valid_payload):
        """Error when instance is None."""
        with pytest.raises(ValueError, match="Catalog item instance is required"):
            service.update_item(None, valid_payload, str(catalog.external_id))

    def test_update_status(self, service, catalog_item):
        """Change item status."""
        assert catalog_item.is_active is True

        service.update_status(catalog_item, is_active=False)
        catalog_item.refresh_from_db()
        assert catalog_item.is_active is False

        service.update_status(catalog_item, is_active=True)
        catalog_item.refresh_from_db()
        assert catalog_item.is_active is True

    def test_retrieve_default_item(self, service, catalog, valid_payload):
        """Retrieve item by priority ensuring service requirements are met."""
        service.register_item(
            {**valid_payload, "priority": 1, "code": "ITEM001"}, str(catalog.external_id)
        )
        service.register_item(
            {**valid_payload, "priority": 5, "code": "ITEM002"}, str(catalog.external_id)
        )

        result = service.retrieve_default_item("ITEM002", catalog.code)

        assert result is not None
        assert result.priority == 5
        assert result.code == "ITEM002"
