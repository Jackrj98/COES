from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from apps.catalogs.layers.applications.catalog_service import CatalogAppService
from apps.catalogs.models import Catalog

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def service():
    return CatalogAppService()


@pytest.fixture
def valid_payload():
    return {
        "name": "Test catalog",
        "code": "TEST001",
        "description": "Test catalog description",
        "priority": 1,
        "is_active": True,
    }


# ---------------------------------------------------------------------------
# retrieve_by_code
# ---------------------------------------------------------------------------


class TestRetrieveByCode:
    @pytest.mark.django_db
    def test_returns_catalog_when_found(self, service, valid_payload):
        service.register_catalog(valid_payload)
        result = service.retrieve_by_code("TEST001")
        assert result is not None
        assert result.code == "TEST001"

    @pytest.mark.django_db
    def test_returns_none_when_not_found(self, service):
        result = service.retrieve_by_code("NONEXISTENT")
        assert result is None


# ---------------------------------------------------------------------------
# retrieve_by_priority
# ---------------------------------------------------------------------------


class TestRetrieveByPriority:
    @pytest.mark.django_db
    def test_returns_catalog_when_found(self, service, valid_payload):
        service.register_catalog(valid_payload)
        result = service.retrieve_by_priority(1)
        assert result is not None
        assert result.priority == 1

    @pytest.mark.django_db
    def test_ignores_inactive_catalogs(self, service, valid_payload):
        catalog = service.register_catalog(valid_payload)
        catalog.is_active = False
        catalog.save()

        result = service.retrieve_by_priority(1)
        assert result is None


# ---------------------------------------------------------------------------
# generate_next_priority
# ---------------------------------------------------------------------------


class TestGenerateNextPriority:
    @pytest.mark.django_db
    def test_returns_one_when_no_catalogs(self, service):
        Catalog.objects.filter(is_active=True).delete()
        assert service.generate_next_priority() == 1

    @pytest.mark.django_db
    def test_returns_max_priority_plus_one(self, service):
        Catalog.objects.create(name="Cat1", code="C1", priority=5, is_active=True)
        Catalog.objects.create(name="Cat2", code="C2", priority=3, is_active=True)

        assert (
            service.generate_next_priority()
            == Catalog.active.filter(is_active=True, deleted_at__isnull=True).last().priority + 1
        )

    @pytest.mark.django_db
    def test_ignores_inactive_catalogs(self, service):
        Catalog.objects.create(name="Active", code="ACT", priority=5, is_active=True)
        Catalog.objects.create(name="Inactive", code="INACT", priority=10, is_active=False)
        assert (
            service.generate_next_priority()
            == Catalog.active.filter(is_active=True, deleted_at__isnull=True).last().priority + 1
        )


# ---------------------------------------------------------------------------
# register_catalog
# ---------------------------------------------------------------------------


class TestRegisterCatalog:
    @pytest.mark.django_db
    def test_success(self, service, valid_payload):
        result = service.register_catalog(valid_payload)
        assert result.code == "TEST001"
        assert result.name == "Test catalog"
        assert result.priority == 1
        assert result.is_active is True
        assert Catalog.objects.filter(code="TEST001").exists()

    @pytest.mark.django_db
    def test_raises_error_on_duplicate_code(self, service, valid_payload):
        service.register_catalog(valid_payload)
        with pytest.raises(ValueError, match="already exists"):
            service.register_catalog(valid_payload)

    @pytest.mark.django_db
    def test_raises_validation_error_on_invalid_payload(self, service):
        invalid_payload = {"name": "Test"}  # Missing required fields
        with pytest.raises(ValidationError):
            service.register_catalog(invalid_payload)


# ---------------------------------------------------------------------------
# update_catalog
# ---------------------------------------------------------------------------


class TestUpdateCatalog:
    @pytest.mark.django_db
    def test_success(self, service, valid_payload):
        catalog = service.register_catalog(valid_payload)
        update_data = {**valid_payload, "name": "Updated name", "priority": 10}

        updated = service.update_catalog(catalog, update_data)

        assert updated.name == "Updated name"
        assert updated.priority == 10
        assert updated.code == "TEST001"

    @pytest.mark.django_db
    def test_raises_error_when_instance_is_none(self, service, valid_payload):
        with pytest.raises(ValueError, match="Catalog instance is required"):
            service.update_catalog(None, valid_payload)

    @pytest.mark.django_db
    def test_raises_error_on_duplicate_code(self, service, valid_payload):
        service.register_catalog(
            {**valid_payload, "code": "EXISTENTE", "name": "Primero", "is_active": True}
        )

        catalog2 = service.register_catalog(
            {**valid_payload, "code": "TEST002", "name": "Segundo", "is_active": True}
        )

        update_data = {**valid_payload, "code": "EXISTENTE", "name": "Nombre"}

        with pytest.raises(ValueError, match="already exists"):
            service.update_catalog(catalog2, update_data)


# ---------------------------------------------------------------------------
# retrieve_catalogs (if actually used)
# ---------------------------------------------------------------------------


class TestRetrieveCatalogs:
    @pytest.mark.django_db
    def test_returns_list_of_catalogs(self, service, valid_payload):
        service.register_catalog(valid_payload)

        params = MagicMock()
        params.items = Catalog.objects.all()
        params.result.return_value = []

        result = service.retrieve_catalogs(params)
        assert result is not None
