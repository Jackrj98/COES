import logging

from django.db import IntegrityError, transaction
from pydantic import ValidationError

from apps.core.layers import BaseAppService
from apps.operations.layers.builders import SupplierBuilder
from apps.operations.layers.dto import DatatableSearch, SupplierDTO
from apps.operations.models import Supplier

logger = logging.getLogger(__name__)


class SupplierAppService(BaseAppService):
    """Service responsible for handling supplier-related operations."""

    def __init__(self):
        super().__init__(Supplier)

    def retrieve_reasons(self):
        try:
            reasons = (
                self.model.objects.filter(deleted_at__isnull=True)
                .values_list("reason", flat=True)
                .distinct()
                .order_by("reason")
            )
            return [(r, r) for r in reasons]
        except Exception as e:
            logger.exception(f"Failed to fetch reasons: {e}")
            return []

    @staticmethod
    def retrieve_suppliers(params):
        fields = [
            "external_id",
            "business_name",
            "contact_name",
            "address",
            "delivery_days",
            "tax_id",
            "phone",
            "email",
            "is_active",
            "created_at",
            "updated_at",
        ]
        try:
            DatatableSearch.retrieve_suppliers(params)
            queryset = params.items
            qs = list(queryset.values(*fields))
            return params.result(qs)
        except Exception as e:
            logger.exception(f"Failed to fetch suppliers: {e}")
            return []

    @transaction.atomic
    def save_supplier(self, payload, instance=None):
        builder = SupplierBuilder(instance) if instance else SupplierBuilder()

        try:
            dto = SupplierDTO(**payload)

            supplier = (
                builder.set_contact_name(dto.contact_name)
                .set_business_name(dto.business_name)
                .set_tax_id(dto.tax_id)
                .set_delivery_days(dto.delivery_days)
                .set_email(dto.email)
                .set_phone(dto.phone)
                .set_address(dto.address)
                .save()
                .build()
            )
            return supplier
        except IntegrityError:
            raise
        except ValidationError as e:
            logger.warning(f"Validation error for payload: {e.json()}")
            raise
        except Exception as e:
            logger.error(f"Error creating supplier: {e}", exc_info=True)
            raise

    def register_supplier(self, payload):
        """Register a new supplier."""
        return self.save_supplier(payload, instance=None)

    def update_supplier(self, instance, payload):
        """Update the status of a supplier."""
        return self.save_supplier(payload=payload, instance=instance)

    @staticmethod
    def update_status(instance):
        builder = SupplierBuilder(supplier=instance)
        try:
            return builder.set_is_active(instance.is_active).save().build()
        except (ValidationError, ValueError) as e:
            logger.warning(f"Error updating status: {e}")
            raise
        except Exception as e:
            logger.error(f"Error update status of supplier: {e}", exc_info=True)
            raise
