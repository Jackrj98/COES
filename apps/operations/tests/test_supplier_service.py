from unittest.mock import MagicMock, patch

import pytest
from django.db import IntegrityError
from pydantic import ValidationError

from apps.operations.layers.applications.supplier_service import SupplierAppService
from apps.operations.models import Supplier

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def service():
    return SupplierAppService()


@pytest.fixture
def mock_supplier():
    mock_supplier = MagicMock(spec=Supplier)
    mock_supplier.external_id = "ext-123"
    mock_supplier.business_name = "Test Supplier"
    return mock_supplier


@pytest.fixture
def valid_payload():
    return {
        "business_name": "Distribuidora Global S.A.",
        "contact_name": "Juan Pérez",
        "address": "Av. Principal 123",
        "delivery_days": 3,
        "email": "ventas@disglobal.ec",
        "phone": "0991234567",
        "tax_id": "2222222222",
    }


@pytest.fixture
def existing_supplier():
    supplier = MagicMock(spec=Supplier)
    supplier.external_id = "ext-456"
    supplier.business_name = "Distribuidora Global S.A."
    supplier.contact_name = "Juan Pérez"
    supplier.address = "Av. Principal 123"
    supplier.tax_id = "41414141414141"
    supplier.delivery_days = 3
    supplier.email = "ventas@disglobal.ec"
    supplier.phone = "0991234567"
    supplier.is_active = True
    return supplier


# ---------------------------------------------------------------------------
# retrieve_reasons
# ---------------------------------------------------------------------------


class TestRetrieveReasons:
    @pytest.mark.django_db
    def test_returns_list_of_tuples(self, service):
        # Mock the queryset
        mock_queryset = MagicMock()
        mock_queryset.filter.return_value.values_list.return_value.distinct.return_value.order_by.return_value = [
            "Insumos industriales",
            "Servicios",
        ]

        with patch.object(service.model.objects, "filter", return_value=mock_queryset):
            result = service.retrieve_reasons()

        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, tuple)
            assert len(item) == 2

    @pytest.mark.django_db
    def test_returns_empty_on_exception(self, service, caplog):
        with patch.object(service.model.objects, "filter", side_effect=Exception("db error")):
            result = service.retrieve_reasons()
        assert result == []
        assert "Failed to fetch reasons" in caplog.text


# ---------------------------------------------------------------------------
# retrieve_suppliers
# ---------------------------------------------------------------------------


class TestRetrieveSuppliers:
    def test_returns_result_on_success(self, service):
        mock_params = MagicMock()
        mock_params.items = MagicMock()
        mock_params.items.values.return_value = []

        with patch(
            "apps.operations.layers.applications.supplier_service.DatatableSearch"
        ) as mock_dt:
            mock_dt.retrieve_suppliers.return_value = None
            mock_params.result.return_value = {"data": []}

            result = service.retrieve_suppliers(mock_params)

        mock_dt.retrieve_suppliers.assert_called_once_with(mock_params)
        mock_params.items.values.assert_called_once()
        mock_params.result.assert_called_once()
        assert result == {"data": []}

    def test_returns_empty_list_on_exception(self, service, caplog):
        mock_params = MagicMock()

        with patch(
            "apps.operations.layers.applications.supplier_service.DatatableSearch"
        ) as mock_dt:
            mock_dt.retrieve_suppliers.side_effect = Exception("query error")
            result = service.retrieve_suppliers(mock_params)

        assert result == []
        assert "Failed to fetch suppliers" in caplog.text


# ---------------------------------------------------------------------------
# save_supplier (private method)
# ---------------------------------------------------------------------------


class TestSaveSupplier:
    @pytest.mark.django_db
    @patch("apps.operations.layers.applications.supplier_service.SupplierBuilder")
    def test_save_supplier_success_without_instance(
        self, mock_builder_class, service, valid_payload
    ):
        mock_instance = mock_builder_class.return_value
        mock_supplier = MagicMock(spec=Supplier)

        # Chain the builder methods
        mock_instance.set_contact_name.return_value = mock_instance
        mock_instance.set_business_name.return_value = mock_instance
        mock_instance.set_tax_id.return_value = mock_instance
        mock_instance.set_delivery_days.return_value = mock_instance
        mock_instance.set_email.return_value = mock_instance
        mock_instance.set_phone.return_value = mock_instance
        mock_instance.set_address.return_value = mock_instance
        mock_instance.save.return_value = mock_instance
        mock_instance.build.return_value = mock_supplier

        result = service.save_supplier(valid_payload, instance=None)

        mock_builder_class.assert_called_once()
        mock_instance.set_contact_name.assert_called_once_with(valid_payload["contact_name"])
        mock_instance.set_business_name.assert_called_once_with(valid_payload["business_name"])
        mock_instance.set_tax_id.assert_called_once_with(valid_payload["tax_id"])
        mock_instance.set_delivery_days.assert_called_once_with(valid_payload["delivery_days"])
        mock_instance.set_email.assert_called_once_with(valid_payload["email"])
        mock_instance.set_phone.assert_called_once_with(valid_payload["phone"])
        mock_instance.set_address.assert_called_once_with(valid_payload["address"])
        mock_instance.save.assert_called_once()
        mock_instance.build.assert_called_once()
        assert result == mock_supplier

    @pytest.mark.django_db
    @patch("apps.operations.layers.applications.supplier_service.SupplierBuilder")
    def test_save_supplier_success_with_instance(
        self, mock_builder_class, service, existing_supplier, valid_payload
    ):
        mock_instance = mock_builder_class.return_value
        mock_supplier = MagicMock(spec=Supplier)

        mock_instance.set_contact_name.return_value = mock_instance
        mock_instance.set_business_name.return_value = mock_instance
        mock_instance.set_tax_id.return_value = mock_instance
        mock_instance.set_delivery_days.return_value = mock_instance
        mock_instance.set_email.return_value = mock_instance
        mock_instance.set_phone.return_value = mock_instance
        mock_instance.set_address.return_value = mock_instance
        mock_instance.save.return_value = mock_instance
        mock_instance.build.return_value = mock_supplier

        result = service.save_supplier(valid_payload, instance=existing_supplier)

        # CORRECCIÓN: El builder recibe 'supplier' como argumento posicional, no 'instance'
        mock_builder_class.assert_called_once_with(existing_supplier)
        mock_instance.save.assert_called_once()
        assert result == mock_supplier

    @pytest.mark.django_db
    @patch("apps.operations.layers.applications.supplier_service.SupplierBuilder")
    def test_save_supplier_raises_integrity_error(self, mock_builder_class, service, valid_payload):
        mock_instance = mock_builder_class.return_value

        mock_instance.set_contact_name.return_value = mock_instance
        mock_instance.set_business_name.return_value = mock_instance
        mock_instance.set_tax_id.return_value = mock_instance
        mock_instance.set_delivery_days.return_value = mock_instance
        mock_instance.set_email.return_value = mock_instance
        mock_instance.set_phone.return_value = mock_instance
        mock_instance.set_address.return_value = mock_instance

        mock_instance.save.side_effect = IntegrityError("duplicate")

        with pytest.raises(IntegrityError):
            service.save_supplier(valid_payload, instance=None)

    @pytest.mark.django_db
    @patch("apps.operations.layers.applications.supplier_service.SupplierBuilder")
    def test_save_supplier_raises_validation_error(
        self, mock_builder_class, service, valid_payload, caplog
    ):
        from pydantic import ValidationError as PydanticValidationError

        # Mock SupplierDTO to raise ValidationError
        with patch(
            "apps.operations.layers.applications.supplier_service.SupplierDTO",
            side_effect=PydanticValidationError.from_exception_data("test", []),
        ):
            with pytest.raises(ValidationError):
                service.save_supplier(valid_payload, instance=None)

            assert "Validation error for payload" in caplog.text

    @pytest.mark.django_db
    @patch("apps.operations.layers.applications.supplier_service.SupplierBuilder")
    def test_save_supplier_raises_general_exception(
        self, mock_builder_class, service, valid_payload, caplog
    ):
        mock_instance = mock_builder_class.return_value
        mock_instance.set_contact_name.side_effect = Exception("Unexpected error")

        with pytest.raises(Exception, match="Unexpected error"):
            service.save_supplier(valid_payload, instance=None)

        assert "Error creating supplier" in caplog.text


# ---------------------------------------------------------------------------
# register_supplier
# ---------------------------------------------------------------------------


class TestRegisterSupplier:
    @pytest.mark.django_db
    @patch("apps.operations.layers.applications.supplier_service.SupplierAppService.save_supplier")
    def test_success(self, mock_save_supplier, service, valid_payload, mock_supplier):
        mock_save_supplier.return_value = mock_supplier

        result = service.register_supplier(valid_payload)

        mock_save_supplier.assert_called_once_with(valid_payload, instance=None)
        assert result == mock_supplier


# ---------------------------------------------------------------------------
# update_supplier
# ---------------------------------------------------------------------------


class TestUpdateSupplier:
    @pytest.mark.django_db
    @patch("apps.operations.layers.applications.supplier_service.SupplierAppService.save_supplier")
    def test_success(
        self, mock_save_supplier, service, existing_supplier, valid_payload, mock_supplier
    ):
        mock_save_supplier.return_value = mock_supplier

        result = service.update_supplier(existing_supplier, valid_payload)

        mock_save_supplier.assert_called_once_with(
            payload=valid_payload, instance=existing_supplier
        )
        assert result == mock_supplier


# ---------------------------------------------------------------------------
# update_status
# ---------------------------------------------------------------------------


class TestUpdateStatus:
    @pytest.mark.django_db
    @patch("apps.operations.layers.applications.supplier_service.SupplierBuilder")
    def test_success(self, mock_builder_class, service, existing_supplier):
        mock_instance = mock_builder_class.return_value
        mock_supplier = MagicMock(spec=Supplier)

        mock_instance.set_is_active.return_value = mock_instance
        mock_instance.save.return_value = mock_instance
        mock_instance.build.return_value = mock_supplier

        result = service.update_status(existing_supplier)

        mock_builder_class.assert_called_once_with(supplier=existing_supplier)
        mock_instance.set_is_active.assert_called_once_with(existing_supplier.is_active)
        mock_instance.save.assert_called_once()
        mock_instance.build.assert_called_once()
        assert result == mock_supplier

    @pytest.mark.django_db
    @patch("apps.operations.layers.applications.supplier_service.SupplierBuilder")
    def test_raises_validation_error(self, mock_builder_class, service, existing_supplier, caplog):
        from pydantic import ValidationError as PydanticValidationError

        mock_instance = mock_builder_class.return_value
        mock_instance.set_is_active.side_effect = PydanticValidationError.from_exception_data(
            "test", []
        )

        with pytest.raises(ValidationError):
            service.update_status(existing_supplier)

        assert "Error updating status" in caplog.text

    @pytest.mark.django_db
    @patch("apps.operations.layers.applications.supplier_service.SupplierBuilder")
    def test_raises_value_error(self, mock_builder_class, service, existing_supplier, caplog):
        mock_instance = mock_builder_class.return_value
        mock_instance.set_is_active.side_effect = ValueError("Invalid state transition")

        with pytest.raises(ValueError, match="Invalid state transition"):
            service.update_status(existing_supplier)

        assert "Error updating status" in caplog.text

    @pytest.mark.django_db
    @patch("apps.operations.layers.applications.supplier_service.SupplierBuilder")
    def test_raises_general_exception(self, mock_builder_class, service, existing_supplier, caplog):
        mock_instance = mock_builder_class.return_value
        mock_instance.set_is_active.side_effect = Exception("Unexpected error")

        with pytest.raises(Exception, match="Unexpected error"):
            service.update_status(existing_supplier)

        assert "Error update status of supplier" in caplog.text
