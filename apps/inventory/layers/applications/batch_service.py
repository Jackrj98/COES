import logging

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import (
    BooleanField,
    Case,
    DateField,
    F,
    Q,
    Sum,
    Value,
    When,
)
from django.db.models.functions import ExtractDay
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.layers import BaseAppService
from apps.inventory.layers.builders import BatchBuilder
from apps.inventory.layers.dto import DatatableSearch
from apps.inventory.models import Batch

logger = logging.getLogger(__name__)


class BatchAppService(BaseAppService):
    """Service responsible for handling supply-related operations."""

    def __init__(self):
        super().__init__(Batch)

    @staticmethod
    def retrieve_batches(params, supply_reference):
        fields = [
            "external_id",
            "batch_number",
            "expiry_date",
            "current_quantity",
            "initial_quantity",
            "unit_cost",
            "status",
            "is_active",
            "created_at",
            "updated_at",
        ]
        try:
            DatatableSearch.retrieve_batches(params, supply_reference)
            queryset = params.items.annotate(
                is_expired=Case(
                    When(expiry_date=timezone.now().date(), then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField(),
                ),
                total_supply_stock=Sum(
                    "supply__batches__current_quantity",
                    filter=Q(supply__batches__status=Batch.StatusChoices.ACTIVE),
                ),
                days_until_expiry=ExtractDay(
                    F("expiry_date") - Value(timezone.now().date(), output_field=DateField())
                ),
            )
            qs = list(
                queryset.values(*fields, "is_expired", "total_supply_stock", "days_until_expiry")
            )
            return params.result(qs)
        except Exception as e:
            logger.exception(f"Failed to fetch batches: {e}")
            return params.result([]) if hasattr(params, "result") else []

    def retrieve_stock_total(self, supply_reference):
        return (
            self.model.active.filter(
                supply__external_id=supply_reference, is_active=True
            ).aggregate(total=models.Sum("current_quantity"))["total"]
            or 0
        )

    def retrieve_by_expiry_date(self, supply_id):
        return (
            self.model.active.filter(is_active=True, supply_id=supply_id, current_quantity__gt=0)
            .select_related("supply")
            .order_by("expiry_date")
        )

    def save_batch(self, payload, instance=None):

        builder = BatchBuilder(batch=instance) if instance else BatchBuilder()
        try:
            batch_instance = (
                builder.set_batch_number(payload.get("batch_number"))
                .set_expiry_date(payload.get("expiry_date"))
                .set_manufacture_date(payload.get("manufacture_date"))
                .set_unit_cost(payload.get("unit_cost"))
                .set_initial_quantity(payload.get("initial_quantity"))
                .set_current_quantity(payload.get("current_quantity"))
                .set_status(payload.get("status"))
                .set_notes(payload.get("notes"))
                .set_is_active(payload.get("is_active"))
                .set_supply(payload.get("supply_id"))
                .set_supplier(payload.get("supplier_id"))
                .build()
            )

            return batch_instance
        except ValidationError as e:
            logger.warning(f"Validation error: {e.error_dict}")
            raise
        except Exception as e:
            logger.error(f"Error saving batch: {e}", exc_info=True)
            raise

    def register_batch(self, payload):
        """Register a new batch item."""
        return self.save_batch(payload, instance=None)

    def update_batch(self, instance, payload):
        """Update an existing supply item."""
        if not instance:
            raise ValueError(_("Batch instance is required."))

        if payload["current_quantity"] == 0:
            payload["status"] = self.model.BatchStatus.DEPLETED.value
        return self.save_batch(payload, instance=instance)

    @staticmethod
    def update_batch_stock(instance, quantity):
        builder = BatchBuilder(instance)
        if quantity == 0:
            builder.set_status(Batch.BatchStatus.DEPLETED.value)
        return builder.set_current_quantity(quantity).build()
