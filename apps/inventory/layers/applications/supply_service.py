import logging

from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Q, Sum
from django.db.models.aggregates import Count
from django.utils.translation import gettext_lazy as _
from pydantic import ValidationError

from apps.core.layers import BaseAppService
from apps.inventory.layers.builders import SupplyBuilder
from apps.inventory.layers.dto import DatatableSearch, SupplyDTO
from apps.inventory.models import Batch, Supply

logger = logging.getLogger(__name__)


class SupplyAppService(BaseAppService):
    """Service responsible for handling supply-related operations."""

    def __init__(self):
        super().__init__(Supply)

    @staticmethod
    def retrieve_suppliers(params):
        fields = [
            "external_id",
            "name",
            "code",
            "description",
            "stock_min",
            "category__name",
            "unit_of_measure__name",
            "unit_of_measure__extra",
            "is_active",
            "created_at",
            "updated_at",
        ]
        try:
            DatatableSearch.retrieve_supplies(params)
            queryset = params.items.annotate(
                stock=Sum("batches__stock", filter=Q(batches__status=Batch.Status.ACTIVE)),
                active_batches_count=Count(
                    "batches", filter=Q(batches__status=Batch.Status.ACTIVE)
                ),
            )

            qs = list(queryset.values(*fields, "stock", "active_batches_count"))
            return params.result(qs)
        except Exception as e:
            logger.exception(f"Failed to fetch supplies: {e}")
            return params.result([]) if hasattr(params, "result") else []

    @staticmethod
    def _generate_unique_code(code):
        import uuid

        if code:
            return f"{code}-{uuid.uuid4().hex[:6].upper()}"
        return f"{uuid.uuid4().hex[:6].upper()}"

    @transaction.atomic
    def save_supply(self, payload, file=None, instance=None):
        builder = SupplyBuilder(supply=instance) if instance else SupplyBuilder()

        try:
            dto = SupplyDTO(**payload)

            supply = (
                builder.set_name(dto.name)
                .set_code(dto.code)
                .set_description(dto.description)
                .set_active(dto.is_active)
                .set_stock_min(dto.stock_min)
                .set_category(dto.category_id)
                .set_unit_of_measure(dto.unit_of_measure_id)
                .save()
            ).build()

            if file:
                self._save_uploaded_file(file=file, instance=supply)

            return supply

        except ValidationError as e:
            logger.warning(f"Validation error: {e.json()}")
            raise
        except Exception as e:
            logger.error(f"Error saving supply: {e}", exc_info=True)
            raise

    @staticmethod
    def _save_uploaded_file(file, instance=None, field_name="image_url"):
        """Save uploaded file and delete old one if exists."""
        if not file or not instance:
            return None

        # Get the old file field value
        old_file_field = getattr(instance, field_name)

        # Delete old file if exists
        if old_file_field and old_file_field.name:
            try:
                if default_storage.exists(old_file_field.name):
                    default_storage.delete(old_file_field.name)
                    logger.info(f"Deleted old file: {old_file_field.name}")
            except Exception as e:
                logger.error(f"Error deleting old file: {e}")
        # Assign and save new file
        setattr(instance, field_name, file)
        instance.save()

        # Return the URL of the new file
        new_file_field = getattr(instance, field_name)
        return new_file_field.url if new_file_field else None

    def register_supply(self, payload, file=None):
        """Register a new supply item."""
        category_code = payload.get("category_code", None)
        payload.pop("category_code", None)
        payload["code"] = self._generate_unique_code(category_code)

        return self.save_supply(payload, file=file, instance=None)

    def update_supply(self, instance, payload, file=None):
        """Update an existing supply item."""
        if not instance:
            raise ValueError(_("Supply instance is required."))

        payload.pop("category_code", None)
        payload["code"] = instance.code
        return self.save_supply(payload, instance=instance, file=file)
