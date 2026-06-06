import logging

from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Q, Sum, Value
from django.db.models.aggregates import Count
from django.db.models.functions import Coalesce
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

    def retrieve_stock_by_code(self, code):
        nrm_code = self.normalize_data(code, remove_spaces=True, to_lowercase=False)
        result = self.model.active.filter(code=nrm_code).aggregate(
            total_stock=Coalesce(Sum("batches__stock"), Value(0))
        )
        return result["total_stock"]

    def retrieve_active(self):
        """Retrieve active supplies with related fields."""
        return (
            self.model.active.filter(is_active=True)
            .select_related("category", "unit_of_measure")
            .order_by("name")
        )

    def retrieve_by_term(self, search_term, movement_type=None):
        queryset = self.model.active.filter(
            Q(name__icontains=search_term) | Q(code__icontains=search_term), is_active=True
        ).select_related("category", "unit_of_measure")

        queryset = queryset.annotate(
            total_stock=Coalesce(Sum("batches__current_quantity"), Value(0))
        )

        # Filtro lógico: Si es salida (type=1), solo insumos con stock > 0
        if movement_type == "1":
            queryset = queryset.filter(total_stock__gt=0)

        return queryset

    def retrieve_active_choices(self):
        try:
            choices = (
                self.model.active.filter(is_active=True)
                .select_related("category", "unit_of_measure")
                .order_by("name")
            )
            return [
                (
                    item.code,
                    f"{item.name} ({item.code}) {item.unit_of_measure.name} {item.unit_of_measure.extra}",
                )
                for item in choices
            ]
        except Exception as e:
            logger.error(f"Error retrieving supplies by category: {e}")
            return []

    def retrieve_by_code(self, code):
        try:
            norm_code = self.normalize_data(code, remove_spaces=True, to_lowercase=False)
            return self.model.active.filter(code=norm_code, is_active=True).first()
        except Exception as e:
            logger.error(f"Error retrieving supply by code: {e}")
            return self.model.active.none()

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
            batch_status = Batch.StatusChoices
            DatatableSearch.retrieve_supplies(params)
            queryset = params.items.annotate(
                stock=Sum(
                    "batches__current_quantity", filter=Q(batches__status=batch_status.ACTIVE)
                ),
                active_batches_count=Count(
                    "batches", filter=Q(batches__status=batch_status.ACTIVE)
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
