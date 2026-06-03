import logging

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
from pydantic import ValidationError

from apps.core.layers import BaseAppService
from apps.inventory.layers.builders import BatchBuilder
from apps.inventory.layers.dto import BatchDTO, DatatableSearch
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
            "number",
            "due_date",
            "stock",
            "purchase_unit_cost",
            "status",
            "purchase_order__order_number",
            "purchase_order__external_id",
            "is_active",
            "created_at",
            "updated_at",
        ]
        try:
            DatatableSearch.retrieve_batches(params, supply_reference)
            queryset = params.items.annotate(
                is_expired=Case(
                    When(due_date=timezone.now().date(), then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField(),
                ),
                total_supply_stock=Sum(
                    "supply__batches__stock", filter=Q(supply__batches__status=Batch.Status.ACTIVE)
                ),
                days_until_expiry=ExtractDay(
                    F("due_date") - Value(timezone.now().date(), output_field=DateField())
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
            ).aggregate(total=models.Sum("stock"))["total"]
            or 0
        )

    def retrieve_by_due_date(self, supply_id):
        return self.model.active.filter(is_active=True, supply_id=supply_id, stock__gt=0).order_by(
            "-due_date"
        )

    @transaction.atomic
    def save_batch(self, payload, instance=None):
        builder = BatchBuilder(batch=instance) if instance else BatchBuilder()

        try:
            dto = BatchDTO(**payload)
            return (
                builder.set_number(dto.number)
                .set_due_date(dto.due_date)
                .set_stock(dto.stock)
                .set_purchase_unit_cost(dto.purchase_unit_cost)
                .set_status(dto.status)
                .set_supply(dto.supply_id)
                .set_purchase_order(dto.purchase_order_id)
                .set_status_by_expiration()
                .save()
                .build()
            )
        except ValidationError as e:
            logger.warning(f"Validation error: {e.json()}")
            raise
        except Exception as e:
            logger.error(f"Error saving batch: {e}", exc_info=True)
            raise

    def register_batch(self, payload):
        """Register a new batch item."""
        return self.save_batch(payload, instance=None)

    def update_batch(self, instance, payload, file=None):
        """Update an existing supply item."""
        if not instance:
            raise ValueError(_("Batch instance is required."))

        payload["supply_id"] = instance.supply_id
        return self.save_batch(payload, instance=instance)

    @staticmethod
    def update_batch_stock(instance, quantity):

        builder = BatchBuilder(instance)
        return builder.set_stock(quantity).save().build()
