import logging

from django.db import transaction
from django.db.models import Count, Max
from django.utils.translation import gettext_lazy as _
from pydantic import ValidationError

from apps.catalogs.layers.builders import CatalogBuilder
from apps.catalogs.layers.dto import CatalogDatatableSearch, CatalogDTO
from apps.catalogs.models import Catalog
from apps.core.layers import BaseAppService

logger = logging.getLogger(__name__)


class CatalogAppService(BaseAppService):
    """Service responsible for handling catalog-related operations."""

    def __init__(self):
        super().__init__(Catalog)

    def retrieve_by_code(self, code):
        normalize_code = self.normalize_data(code, remove_spaces=True, to_lowercase=False)
        return self.model.active.filter(code=normalize_code).first()

    def retrieve_by_priority(self, priority):
        return self.model.active.filter(priority=priority, is_active=True).first()

    def generate_next_priority(self):
        """Generate the next available priority for a catalog."""
        max_priority = self.model.active.filter(is_active=True).aggregate(
            max_priority=Max("priority")
        )["max_priority"]

        # Handle case when no items exist
        return (max_priority or 0) + 1

    @staticmethod
    def retrieve_catalogs(params):
        fields = [
            "external_id",
            "name",
            "code",
            "description",
            "priority",
            "is_active",
            "created_at",
            "updated_at",
        ]
        try:
            CatalogDatatableSearch.retrieve_catalogs(params)
            queryset = params.items.annotate(items_count=Count("items"))

            return params.result(list(queryset.values(*fields, "items_count")))
        except Exception as e:
            logger.exception(f"Failed to fetch catalogs: {e}")
            return params.result([]) if hasattr(params, "result") else []

    def _validate_unique_code(self, code, instance=None):
        """Validate that the code is unique within the catalog."""
        queryset = self.model.active.filter(code=code)
        if instance:
            queryset = queryset.exclude(id=instance.id)

        if queryset.exists():
            raise ValueError(_("Catalog item with this code already exists in this catalog."))

    @transaction.atomic
    def save_catalog(self, payload, instance=None):
        """Create or update a catalog.

        Args:
            payload: Dictionary with item data
            instance: Optional existing instance for update

        Returns:
            CatalogItem: The saved catalog item
        """
        # Initialize builder with existing instance or new one
        builder = CatalogBuilder(catalog=instance) if instance else CatalogBuilder()
        action = "updating" if instance else "creating"

        try:
            dto = CatalogDTO(**payload)
            self._validate_unique_code(dto.code, instance)
            catalog = (
                builder.set_name(dto.name)
                .set_code(dto.code)
                .set_description(dto.description)
                .set_priority(dto.priority)
                .set_active(dto.is_active)
                .save()
            )
            return catalog.build()
        except ValidationError as e:
            logger.warning(f"Validation error {action} catalog: {e.json()}")
            raise
        except Exception as e:
            logger.error(f"Error {action} catalog: {e}", exc_info=True)
            raise

    def register_catalog(self, payload):
        """Register a new catalog item."""
        return self.save_catalog(payload, instance=None)

    def update_catalog(self, instance, payload):
        """Update an existing catalog item."""
        if not instance:
            raise ValueError(_("Catalog instance is required."))
        return self.save_catalog(payload, instance=instance)
