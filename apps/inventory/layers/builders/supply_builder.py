from apps.inventory.models import Supply


class SupplyBuilder:
    """Builder for a Supply model."""

    def __init__(self, supply=None):
        self.supply = supply or Supply()

    def set_name(self, name: str) -> "SupplyBuilder":
        if name:
            self.supply.name = name.strip().capitalize()
        return self

    def set_code(self, code: str) -> "SupplyBuilder":
        if code:
            clean_code = "".join(
                c
                for c in code.strip().upper().replace(" ", "_")
                if c.isalnum() or c == "_" or c == "-"
            )
            self.supply.code = clean_code
        return self

    def set_description(self, description: str) -> "SupplyBuilder":
        if description:
            self.supply.description = description.strip()
        return self

    def set_stock_min(self, stock_min: int) -> "SupplyBuilder":
        """Set a supply stock_min."""
        self.supply.stock_min = stock_min
        return self

    def set_image_url(self, image_url: str) -> "SupplyBuilder":
        """Set a supply image_url."""
        self.supply.image_url = image_url
        return self

    def set_category(self, category: int) -> "SupplyBuilder":
        """Set a supply category."""
        self.supply.category_id = category
        return self

    def set_unit_of_measure(self, unit_of_measure: int) -> "SupplyBuilder":
        """Set a supply unit_of_measure."""
        self.supply.unit_of_measure_id = unit_of_measure
        return self

    def set_active(self, is_active: bool = True) -> "SupplyBuilder":
        """Set supply active status."""
        self.supply.is_active = is_active
        return self

    def save(self) -> "SupplyBuilder":
        """Save the supply to a database."""
        self.supply.save()
        return self

    def build(self) -> Supply:
        """Build and return a supply instance."""
        return self.supply
