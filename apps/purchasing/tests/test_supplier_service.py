from unittest.mock import MagicMock, patch

import pytest
from django.db import IntegrityError

from apps.purchasing.layers.applications.supplier_service import SupplierAppService
from apps.purchasing.models import Supplier

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def service():
    return SupplierAppService()


@pytest.fixture
def mock_supplier():
    with patch(
        "apps.purchasing.layers.applications.supplier_service.SupplierBuilder"
    ) as mock_class:
        instance = mock_class.return_value
        supplier = MagicMock(spec=Supplier)
        instance.build.return_value = supplier
        yield supplier


@pytest.fixture
def valid_payload():
    return {
        "business_name": "Distribuidora Global S.A.",
        "reason": "Insumos industriales",
        "tax_id": "2222222222",
        "delivery_days": 3,
        "email": "ventas@disglobal.ec",
        "phone": "0991234567",
    }


@pytest.fixture
def existing_supplier():
    supplier = MagicMock(spec=Supplier)
    supplier.business_name = "Distribuidora Global S.A."
    supplier.reason = "Insumos industriales"
    supplier.tax_id = "1790012345001"
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
        result = service.retrieve_reasons()
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, tuple)
            assert len(item) == 2

    @pytest.mark.django_db
    def test_returns_empty_on_exception(self, service, caplog):
        with patch.object(Supplier.objects, "filter", side_effect=Exception("db error")):
            result = service.retrieve_reasons()
        assert result == []
        assert "Failed to fetch reasons" in caplog.text


# ---------------------------------------------------------------------------
# retrieve_suppliers
# ---------------------------------------------------------------------------


class TestRetrieveSuppliers:
    def test_returns_result_on_success(self, service):
        mock_params = MagicMock()
        mock_params.items.values.return_value = []
        mock_params.result.return_value = {"data": []}

        with patch(
            "apps.purchasing.layers.applications.supplier_service.DatatableSearch"
        ) as mock_dt:
            mock_dt.retrieve_suppliers.return_value = None
            result = SupplierAppService.retrieve_suppliers(mock_params)

        assert result == {"data": []}

    def test_returns_empty_list_on_exception(self, service, caplog):
        mock_params = MagicMock()

        with patch(
            "apps.purchasing.layers.applications.supplier_service.DatatableSearch"
        ) as mock_dt:
            mock_dt.retrieve_suppliers.side_effect = Exception("query error")
            result = SupplierAppService.retrieve_suppliers(mock_params)

        assert result == []
        assert "Failed to fetch suppliers" in caplog.text


# ---------------------------------------------------------------------------
# register_supplier
# ---------------------------------------------------------------------------


class TestRegisterSupplier:
    @pytest.mark.django_db
    @patch("apps.purchasing.layers.applications.supplier_service.SupplierBuilder")
    def test_success(self, mock_builder_class, service, valid_payload):
        mock_instance = mock_builder_class.return_value
        mock_instance.create_supplier.return_value = mock_instance
        mock_supplier = MagicMock(spec=Supplier)
        mock_instance.build.return_value = mock_supplier

        result = service.register_supplier(valid_payload)

        mock_instance.create_supplier.assert_called_once_with(
            business_name=valid_payload["business_name"],
            reason=valid_payload["reason"],
            tax_id=valid_payload["tax_id"],
            delivery_days=valid_payload["delivery_days"],
            email=valid_payload["email"],
            phone=valid_payload["phone"],
        )
        mock_instance.build.assert_called_once()
        assert result == mock_supplier

    @pytest.mark.django_db
    @patch("apps.purchasing.layers.applications.supplier_service.SupplierBuilder")
    def test_raises_integrity_error(self, mock_builder_class, service, valid_payload):
        mock_instance = mock_builder_class.return_value
        mock_instance.create_supplier.return_value = mock_instance
        mock_instance.build.side_effect = IntegrityError("duplicate")

        with pytest.raises(IntegrityError):
            service.register_supplier(valid_payload)

    @pytest.mark.django_db
    def test_raises_validation_error_on_invalid_payload(self, service, caplog):
        invalid_payload = {"business_name": "X", "reason": "Y"}  # faltan campos

        with pytest.raises(Exception):
            service.register_supplier(invalid_payload)

    @pytest.mark.django_db
    @patch("apps.purchasing.layers.applications.supplier_service.SupplierBuilder")
    def test_raises_general_exception(self, mock_builder_class, service, valid_payload, caplog):
        mock_instance = mock_builder_class.return_value
        mock_instance.create_supplier.side_effect = Exception("Unexpected error")

        with pytest.raises(Exception, match="Unexpected error"):
            service.register_supplier(valid_payload)

        assert "Error creating supplier" in caplog.text


# ---------------------------------------------------------------------------
# update_supplier
# ---------------------------------------------------------------------------


class TestUpdateSupplier:
    @pytest.mark.django_db
    @patch("apps.purchasing.layers.applications.supplier_service.SupplierBuilder")
    def test_success(self, mock_builder_class, service, existing_supplier, valid_payload):
        mock_instance = mock_builder_class.return_value
        mock_instance.update_supplier.return_value = mock_instance
        mock_supplier = MagicMock(spec=Supplier)
        mock_instance.build.return_value = mock_supplier

        result = service.update_supplier(existing_supplier, valid_payload)

        mock_builder_class.assert_called_once_with(supplier=existing_supplier)
        mock_instance.update_supplier.assert_called_once()
        mock_instance.build.assert_called_once()
        assert result == mock_supplier

    @pytest.mark.django_db
    @patch("apps.purchasing.layers.applications.supplier_service.SupplierBuilder")
    def test_raises_integrity_error(
        self, mock_builder_class, service, existing_supplier, valid_payload
    ):
        mock_instance = mock_builder_class.return_value
        mock_instance.update_supplier.return_value = mock_instance
        mock_instance.build.side_effect = IntegrityError("duplicate email")

        with pytest.raises(IntegrityError):
            service.update_supplier(existing_supplier, valid_payload)

    @pytest.mark.django_db
    @patch("apps.purchasing.layers.applications.supplier_service.SupplierBuilder")
    def test_raises_general_exception(
        self, mock_builder_class, service, existing_supplier, valid_payload, caplog
    ):
        mock_instance = mock_builder_class.return_value
        mock_instance.update_supplier.side_effect = Exception("Unexpected error")

        with pytest.raises(Exception, match="Unexpected error"):
            service.update_supplier(existing_supplier, valid_payload)

        assert "Error update supplier" in caplog.text


# ---------------------------------------------------------------------------
# update_status
# ---------------------------------------------------------------------------


class TestUpdateStatus:
    @pytest.mark.django_db
    @patch("apps.purchasing.layers.applications.supplier_service.SupplierBuilder")
    def test_success(self, mock_builder_class, service, existing_supplier):
        mock_instance = mock_builder_class.return_value
        mock_instance.change_status.return_value = mock_instance
        mock_supplier = MagicMock(spec=Supplier)
        mock_instance.build.return_value = mock_supplier

        result = service.update_status(existing_supplier)

        mock_builder_class.assert_called_once_with(supplier=existing_supplier)
        mock_instance.change_status.assert_called_once()
        mock_instance.build.assert_called_once()
        assert result == mock_supplier

    @pytest.mark.django_db
    @patch("apps.purchasing.layers.applications.supplier_service.SupplierBuilder")
    def test_raises_value_error(self, mock_builder_class, service, existing_supplier, caplog):
        mock_instance = mock_builder_class.return_value
        mock_instance.change_status.side_effect = ValueError("Invalid state transition")

        with pytest.raises(ValueError, match="Invalid state transition"):
            service.update_status(existing_supplier)

        assert "Error updating status" in caplog.text

    @pytest.mark.django_db
    @patch("apps.purchasing.layers.applications.supplier_service.SupplierBuilder")
    def test_raises_general_exception(self, mock_builder_class, service, existing_supplier, caplog):
        mock_instance = mock_builder_class.return_value
        mock_instance.change_status.side_effect = Exception("Unexpected error")

        with pytest.raises(Exception, match="Unexpected error"):
            service.update_status(existing_supplier)

        assert "Error update status of supplier" in caplog.text
