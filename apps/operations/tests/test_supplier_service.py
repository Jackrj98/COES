from unittest.mock import MagicMock, patch

import pytest
from django.db import IntegrityError

from apps.operations.layers.applications import SupplierAppService
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
        "first_name": "Juan",
        "last_name": "Pérez",
        "address": "Av. Principal 123",
        "delivery_days": 3,
        "email": "ventas@disglobal.ec",
        "phone": "0991234567",
        "document_number": "2222222222",
    }


@pytest.fixture
def existing_supplier():
    supplier = MagicMock(spec=Supplier)
    supplier.external_id = "ext-456"
    supplier.business_name = "Distribuidora Global S.A."
    supplier.first_name = "Juan"
    supplier.last_name = "Pérez"
    supplier.address = "Av. Principal 123"
    supplier.document_number = "41414141414141"
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
    @pytest.mark.django_db
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

    @pytest.mark.django_db
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
        mock_builder = mock_builder_class.return_value
        mock_supplier = MagicMock(spec=Supplier)

        # Configure the builder chain
        mock_builder.set_first_name.return_value = mock_builder
        mock_builder.set_last_name.return_value = mock_builder
        mock_builder.set_document_number.return_value = mock_builder
        mock_builder.set_business_name.return_value = mock_builder
        mock_builder.set_delivery_days.return_value = mock_builder
        mock_builder.set_email.return_value = mock_builder
        mock_builder.set_phone.return_value = mock_builder
        mock_builder.set_address.return_value = mock_builder
        mock_builder.build.return_value = mock_supplier

        result = service.save_supplier(valid_payload, instance=None)

        # Verify builder was created without arguments for new instance
        mock_builder_class.assert_called_once_with()

        # Verify all setters were called
        mock_builder.set_first_name.assert_called_once_with(valid_payload["first_name"])
        mock_builder.set_last_name.assert_called_once_with(valid_payload["last_name"])
        mock_builder.set_document_number.assert_called_once_with(valid_payload["document_number"])
        mock_builder.set_business_name.assert_called_once_with(valid_payload["business_name"])
        mock_builder.set_delivery_days.assert_called_once_with(valid_payload["delivery_days"])
        mock_builder.set_email.assert_called_once_with(valid_payload["email"])
        mock_builder.set_phone.assert_called_once_with(valid_payload["phone"])
        mock_builder.set_address.assert_called_once_with(valid_payload["address"])
        mock_builder.build.assert_called_once()

        assert result == mock_supplier

    @pytest.mark.django_db
    @patch("apps.operations.layers.applications.supplier_service.SupplierBuilder")
    def test_save_supplier_success_with_instance(
        self, mock_builder_class, service, existing_supplier, valid_payload
    ):
        mock_builder = mock_builder_class.return_value
        mock_supplier = MagicMock(spec=Supplier)

        # Configure the builder chain
        mock_builder.set_first_name.return_value = mock_builder
        mock_builder.set_last_name.return_value = mock_builder
        mock_builder.set_document_number.return_value = mock_builder
        mock_builder.set_business_name.return_value = mock_builder
        mock_builder.set_delivery_days.return_value = mock_builder
        mock_builder.set_email.return_value = mock_builder
        mock_builder.set_phone.return_value = mock_builder
        mock_builder.set_address.return_value = mock_builder
        mock_builder.build.return_value = mock_supplier

        result = service.save_supplier(valid_payload, instance=existing_supplier)

        # Verify builder was created with existing supplier
        mock_builder_class.assert_called_once_with(existing_supplier)

        # Verify setters were called
        mock_builder.set_first_name.assert_called_once_with(valid_payload["first_name"])
        mock_builder.set_last_name.assert_called_once_with(valid_payload["last_name"])
        mock_builder.set_document_number.assert_called_once_with(valid_payload["document_number"])
        mock_builder.set_business_name.assert_called_once_with(valid_payload["business_name"])
        mock_builder.set_delivery_days.assert_called_once_with(valid_payload["delivery_days"])
        mock_builder.set_email.assert_called_once_with(valid_payload["email"])
        mock_builder.set_phone.assert_called_once_with(valid_payload["phone"])
        mock_builder.set_address.assert_called_once_with(valid_payload["address"])
        mock_builder.build.assert_called_once()

        assert result == mock_supplier

    @pytest.mark.django_db
    @patch("apps.operations.layers.applications.supplier_service.SupplierBuilder")
    def test_save_supplier_raises_integrity_error(self, mock_builder_class, service, valid_payload):
        mock_builder = mock_builder_class.return_value

        # Configure builder chain
        mock_builder.set_first_name.return_value = mock_builder
        mock_builder.set_last_name.return_value = mock_builder
        mock_builder.set_document_number.return_value = mock_builder
        mock_builder.set_business_name.return_value = mock_builder
        mock_builder.set_delivery_days.return_value = mock_builder
        mock_builder.set_email.return_value = mock_builder
        mock_builder.set_phone.return_value = mock_builder
        mock_builder.set_address.return_value = mock_builder
        mock_builder.build.side_effect = IntegrityError("duplicate")

        with pytest.raises(IntegrityError):
            service.save_supplier(valid_payload, instance=None)

    @pytest.mark.django_db
    def test_save_supplier_raises_validation_error(self, service, valid_payload, caplog):
        """Test validation error handling in save_supplier."""
        from pydantic import ValidationError as PydanticValidationError

        # Mock SupplierBuilder to raise ValidationError
        with patch(
            "apps.operations.layers.applications.supplier_service.SupplierBuilder"
        ) as mock_builder_class:
            mock_builder = mock_builder_class.return_value
            mock_builder.set_first_name.return_value = mock_builder
            mock_builder.set_last_name.return_value = mock_builder
            mock_builder.set_document_number.return_value = mock_builder
            mock_builder.set_business_name.return_value = mock_builder
            mock_builder.set_delivery_days.return_value = mock_builder
            mock_builder.set_email.return_value = mock_builder
            mock_builder.set_phone.return_value = mock_builder
            mock_builder.set_address.return_value = mock_builder

            # Correct way to create a Pydantic ValidationError
            try:
                # This will raise a ValidationError that we can catch
                from pydantic import BaseModel

                class TestModel(BaseModel):
                    field: str

                TestModel(field=None)  # This will raise ValidationError
            except PydanticValidationError as e:
                mock_builder.build.side_effect = e

            with pytest.raises(PydanticValidationError):
                service.save_supplier(valid_payload, instance=None)

            assert "Validation error for payload" in caplog.text

    @pytest.mark.django_db
    @patch("apps.operations.layers.applications.supplier_service.SupplierBuilder")
    def test_save_supplier_raises_general_exception(
        self, mock_builder_class, service, valid_payload, caplog
    ):
        mock_builder = mock_builder_class.return_value
        mock_builder.set_first_name.side_effect = Exception("Unexpected error")

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
        mock_builder = mock_builder_class.return_value
        mock_supplier = MagicMock(spec=Supplier)

        mock_builder.set_is_active.return_value = mock_builder
        mock_builder.build.return_value = mock_supplier

        result = service.update_status(existing_supplier)

        mock_builder_class.assert_called_once_with(supplier=existing_supplier)
        mock_builder.set_is_active.assert_called_once_with(existing_supplier.is_active)
        mock_builder.build.assert_called_once()
        assert result == mock_supplier

    @pytest.mark.django_db
    @patch("apps.operations.layers.applications.supplier_service.SupplierBuilder")
    def test_raises_validation_error(self, mock_builder_class, service, existing_supplier, caplog):
        from django.core.exceptions import ValidationError as DjangoValidationError

        mock_builder = mock_builder_class.return_value
        mock_builder.set_is_active.side_effect = DjangoValidationError("Validation error")

        with pytest.raises(DjangoValidationError):
            service.update_status(existing_supplier)

        assert "Error update status of supplier" in caplog.text

    @pytest.mark.django_db
    @patch("apps.operations.layers.applications.supplier_service.SupplierBuilder")
    def test_raises_value_error(self, mock_builder_class, service, existing_supplier, caplog):
        mock_builder = mock_builder_class.return_value
        mock_builder.set_is_active.side_effect = ValueError("Invalid state transition")

        with pytest.raises(ValueError, match="Invalid state transition"):
            service.update_status(existing_supplier)

        assert "Error updating status" in caplog.text

    @pytest.mark.django_db
    @patch("apps.operations.layers.applications.supplier_service.SupplierBuilder")
    def test_raises_general_exception(self, mock_builder_class, service, existing_supplier, caplog):
        mock_builder = mock_builder_class.return_value
        mock_builder.set_is_active.side_effect = Exception("Unexpected error")

        with pytest.raises(Exception, match="Unexpected error"):
            service.update_status(existing_supplier)

        assert "Error update status of supplier" in caplog.text
