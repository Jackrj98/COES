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

    @transaction.atomic
    def save_supply(self, payload, file=None, instance=None):

        builder = SupplyBuilder(supply=instance) if instance else SupplyBuilder()
        action = "updating" if instance else "creating"

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
            )

            if file:
                self._save_uploaded_file(file, instance=supply)

            return supply.build()
        except ValidationError as e:
            logger.warning(f"Validation error {action} supply: {e.json()}")
            raise
        except Exception as e:
            logger.error(f"Error {action} supply: {e}", exc_info=True)
            raise

    @staticmethod
    def _delete_old_image(instance, field_name="image_url"):
        """Delete an old image file from storage."""
        try:
            old_file = getattr(instance, field_name, None)
            if old_file and old_file.name:
                old_file.delete(save=False)
        except Exception as e:
            logger.warning(f"Error deleting old image: {e}")

    def _save_uploaded_file(self, file, instance=None, field_name="image_url"):
        """Save the uploaded file to an instance or return URL."""
        try:
            if instance:
                self._delete_old_image(instance, field_name)
                setattr(instance, field_name, file)
                instance.save(update_fields=[field_name])
                return getattr(instance, field_name).url if getattr(instance, field_name) else None

            file_path = default_storage.save(f"supplies/{file.name}", file)
            return default_storage.url(file_path)

        except Exception as e:
            logger.error(f"Error saving file: {e}", exc_info=True)
            return None

    def register_supply(self, payload):
        """Register a new supply item."""
        return self.save_supply(payload, instance=None)

    def update_supply(self, instance, payload):
        """Update an existing supply item."""
        if not instance:
            raise ValueError(_("Supply instance is required."))
        return self.save_supply(payload, instance=instance)
