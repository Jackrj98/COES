import logging

from django.db import IntegrityError, transaction
from pydantic import ValidationError

from apps.core.layers import BaseAppService
from apps.purchasing.layers.builders import SupplierBuilder
from apps.purchasing.layers.dto import DatatableSearch, SupplierDTO
from apps.purchasing.models import Supplier

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
            "reason",
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
    def register_supplier(self, payload):
        builder = SupplierBuilder()

        try:
            dto = SupplierDTO(**payload)
            return builder.create_supplier(
                business_name=dto.business_name,
                reason=dto.reason,
                tax_id=dto.tax_id,
                delivery_days=dto.delivery_days,
                email=dto.email,
                phone=dto.phone,
            ).build()
        except IntegrityError:
            raise
        except ValidationError as e:
            logger.warning(f"Validation error for payload: {e.json()}")
            raise
        except Exception as e:
            logger.error(f"Error creating supplier: {e}", exc_info=True)
            raise

    @transaction.atomic
    def update_supplier(self, instance, payload):
        builder = SupplierBuilder(supplier=instance)

        try:
            dto = SupplierDTO(**payload)
            return builder.update_supplier(
                business_name=dto.business_name,
                reason=dto.reason,
                tax_id=dto.tax_id,
                delivery_days=dto.delivery_days,
                email=dto.email,
                phone=dto.phone,
            ).build()
        except IntegrityError:
            raise
        except ValidationError as e:
            logger.warning(f"Validation error for payload: {e.json()}")
            raise
        except Exception as e:
            logger.error(f"Error update supplier: {e}", exc_info=True)
            raise

    def update_status(self, instance):
        builder = SupplierBuilder(supplier=instance)

        try:
            return builder.change_status().build()
        except (ValidationError, ValueError) as e:
            logger.warning(f"Error updating status: {e}")
            raise
        except Exception as e:
            logger.error(f"Error update status of supplier: {e}", exc_info=True)
            raise
