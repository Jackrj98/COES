from apps.catalogs.models import Catalog


class CatalogBuilder:
    """Builder for a Catalog model."""

    def __init__(self, catalog=None):
        self.catalog = catalog or Catalog()
        self._created = False

    def set_name(self, name: str) -> "CatalogBuilder":
        """Set catalog name."""
        self.catalog.name = name.strip().lower().capitalize()
        return self

    def set_code(self, code: str) -> "CatalogBuilder":
        """Set catalog code."""
        if not code or code.strip() == "":
            raise ValueError("Catalog code cannot be empty")

        code = code.strip().upper()
        code = code.replace(" ", "_")
        code = "".join(c for c in code if c.isalnum() or c == "_")
        self.catalog.code = code
        return self

    def set_description(self, description: str) -> "CatalogBuilder":
        """Set catalog description."""
        self.catalog.description = description
        return self

    def set_priority(self, priority: int) -> "CatalogBuilder":
        """Set catalog priority."""
        self.catalog.priority = priority
        return self

    def set_active(self, is_active: bool = True) -> "CatalogBuilder":
        """Set catalog active status."""
        self.catalog.is_active = is_active
        return self

    def build(self) -> Catalog:
        """Build and return a catalog instance."""
        self.catalog.full_clean()
        self.catalog.save()
        return self.catalog
