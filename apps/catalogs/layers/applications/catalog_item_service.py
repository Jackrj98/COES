import logging

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils.translation import gettext_lazy as _

from apps.catalogs.layers.builders import CatalogItemBuilder
from apps.catalogs.layers.dto import CatalogDatatableSearch
from apps.catalogs.models import Catalog, CatalogItem
from apps.core.layers import BaseAppService

logger = logging.getLogger(__name__)


class CatalogItemAppService(BaseAppService):
    """Service responsible for handling catalog item-related operations."""

    def __init__(self):
        super().__init__(CatalogItem)

    def _get_queryset_by_code(self, code, catalog_code):
        """Base method - internal use only."""
        if not code or not catalog_code:
            raise ValueError(_("Code and catalog code are required."))

        norm_code = self.normalize_data(code, remove_spaces=True, to_lowercase=False)
        norm_ctg_code = self.normalize_data(catalog_code, remove_spaces=True, to_lowercase=False)

        return self.model.active.filter(code=norm_code, catalog__code=norm_ctg_code).select_related(
            "catalog"
        )

    @staticmethod
    def retrieve_catalog_by_external(catalog_reference):
        """Retrieve catalog by external reference."""
        try:
            return Catalog.objects.get(external_id=catalog_reference)
        except Catalog.DoesNotExist:
            raise ValueError(_("Catalog with the provided reference does not exist."))

    def retrieve_by_code(self, code, catalog_code):
        """Retrieve catalog item by code and catalog code."""
        return self._get_queryset_by_code(code, catalog_code).first()

    def retrieve_default_item(self, code, catalog_code):
        """Retrieve the default item (the highest priority) by code and catalog code."""
        return self._get_queryset_by_code(code, catalog_code).order_by("-priority").first()

    def retrieve_catalog_items(self, catalog_code):
        if not catalog_code:
            raise ValueError(_("Catalog code is required."))

        norm_ctg_code = self.normalize_data(catalog_code, remove_spaces=True, to_lowercase=False)
        queryset = self.model.active.filter(catalog__code=norm_ctg_code, is_active=True)
        return queryset.order_by("-priority")

    def retrieve_by_priority(self, catalog_code, priority):
        norm_ctg_code = self.normalize_data(catalog_code, remove_spaces=True, to_lowercase=False)

        return self.model.active.filter(
            priority=priority, is_active=True, catalog__code=norm_ctg_code
        ).first()

    def generate_next_priority(self, catalog_code):
        """Generate the next available priority for a catalog."""
        norm_ctg_code = self.normalize_data(catalog_code, remove_spaces=True, to_lowercase=False)

        max_priority = self.model.active.filter(
            catalog__code=norm_ctg_code, is_active=True
        ).aggregate(max_priority=Max("priority"))["max_priority"]

        # Handle case when no items exist
        return (max_priority or 0) + 1

    @staticmethod
    def retrieve_items(params, catalog_reference):
        if not catalog_reference:
            raise ValueError(_("Catalog reference is not allowed."))

        fields = [
            "external_id",
            "name",
            "code",
            "description",
            "priority",
            "is_active",
            "extra",
            "created_at",
            "updated_at",
        ]
        try:
            CatalogDatatableSearch.retrieve_catalog_items(params, catalog_reference)
            queryset = params.items
            return params.result(list(queryset.values(*fields)))
        except Exception as e:
            logger.exception(f"Failed to fetch catalogs: {e}")
            return params.result([]) if hasattr(params, "result") else []

    @transaction.atomic
    def save_item(self, payload, instance=None):
        """Create or update a catalog item.

        Args:
            payload: Dictionary with item data
            instance: Optional existing instance for update

        Returns:
            CatalogItem: The saved catalog item
        """
        # Initialize builder with existing instance or new one
        builder = CatalogItemBuilder(item=instance) if instance else CatalogItemBuilder()
        action = "updating" if instance else "creating"

        try:
            catalog_item = (
                builder.set_name(payload.get("name"))
                .set_code(payload.get("code"))
                .set_description(payload.get("description"))
                .set_priority(payload.get("priority"))
                .set_active(payload.get("is_active"))
                .set_extra(payload.get("extra"))
                .set_catalog(payload.get("catalog_id"))
            )
            return catalog_item.build()
        except ValidationError as e:
            logger.warning(f"Validation error {action} catalog item: {e.error_dict}")
            raise
        except Exception as e:
            logger.error(f"Error {action} catalog item: {e}", exc_info=True)
            raise

    def register_item(self, payload, catalog_reference):
        """Register a new catalog item."""
        catalog = self.retrieve_catalog_by_external(catalog_reference)
        payload["catalog_id"] = catalog.id
        return self.save_item(payload, instance=None)

    def update_item(self, instance, payload, catalog_reference):
        """Update an existing catalog item."""
        catalog = self.retrieve_catalog_by_external(catalog_reference)

        if not instance:
            raise ValueError(_("Catalog item instance is required."))

        payload["catalog_id"] = catalog.id
        return self.save_item(payload, instance=instance)

    @staticmethod
    def update_status(instance, is_active=True):
        """Update catalog item status."""
        if not instance:
            raise ValueError(_("Catalog item instance is required."))

        builder = CatalogItemBuilder(item=instance)

        try:
            catalog_item = builder.set_active(is_active).build()
            return catalog_item
        except Exception as e:
            logger.error(
                f"Error updating status of catalog item {instance.code}: {e}", exc_info=True
            )
            raise
