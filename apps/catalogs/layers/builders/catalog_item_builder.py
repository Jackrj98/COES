# builders/catalog_item_builder.py
from apps.catalogs.models import CatalogItem


class CatalogItemBuilder:
    """Builder for CatalogItem model."""

    def __init__(self, item=None):
        self.item = item or CatalogItem()

    def set_name(self, name: str) -> "CatalogItemBuilder":
        """Set the item name."""
        self.item.name = name.strip().lower().capitalize()
        return self

    def set_code(self, code: str) -> "CatalogItemBuilder":
        """Set item code."""
        if not code or code.strip() == "":
            raise ValueError("Item code cannot be empty")
        code = code.strip().upper()
        code = code.replace(" ", "_")
        code = "".join(c for c in code if c.isalnum() or c == "_")
        self.item.code = code
        return self

    def set_description(self, description: str) -> "CatalogItemBuilder":
        """Set item description."""
        self.item.description = description
        return self

    def set_priority(self, priority: int) -> "CatalogItemBuilder":
        """Set item priority."""
        self.item.priority = priority
        return self

    def set_extra(self, extra: str) -> "CatalogItemBuilder":
        """Set an extra value."""
        self.item.extra = extra.title()
        return self

    def set_catalog(self, catalog_id: int) -> "CatalogItemBuilder":
        """Set catalog reference."""
        self.item.catalog_id = catalog_id
        return self

    def set_active(self, is_active: bool = True) -> "CatalogItemBuilder":
        """Set the item active status."""
        self.item.is_active = is_active
        return self

    def save(self) -> "CatalogItemBuilder":
        """Save catalog item to a database."""
        self.item.save()
        return self

    def build(self) -> CatalogItem:
        """Build and return a catalog item instance."""
        # self.item.full_clean()
        self.item.save()
        return self.item
