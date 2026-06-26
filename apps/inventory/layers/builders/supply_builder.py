from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.inventory.models import Supply


class SupplyBuilder:
    """Builder for a Supply model."""

    def __init__(self, supply=None):
        self.supply = supply or Supply()

    def set_name(self, name: str) -> "SupplyBuilder":
        if not name or str(name).strip() == "":
            raise ValidationError({"name": [_("This field cannot be blank.")]})

        self.supply.name = name.strip().capitalize()
        return self

    def set_code(self, code: str) -> "SupplyBuilder":
        if not code or str(code).strip() == "":
            raise ValidationError({"code": [_("This field cannot be blank.")]})

        clean_code = "".join(
            c for c in code.strip().upper().replace(" ", "_") if c.isalnum() or c == "_" or c == "-"
        )
        self.supply.code = clean_code
        return self

    def set_barcode(self, barcode: str) -> "SupplyBuilder":
        if not barcode or str(barcode).strip() == "":
            raise ValidationError({"barcode": [_("This field cannot be blank.")]})

        self.supply.barcode = barcode.strip()
        return self

    def set_description(self, description: str) -> "SupplyBuilder":
        if description:
            self.supply.description = description.strip()
        return self

    def set_stock_min(self, stock_min: int) -> "SupplyBuilder":
        """Set a supply stock_min."""
        if stock_min is None or stock_min == 0:
            raise ValidationError({"stock_min": [_("This field cannot be zero or negative.")]})
        self.supply.stock_min = stock_min
        return self

    def set_stock_max(self, max_stock: int) -> "SupplyBuilder":
        self.supply.stock_max = int(max_stock)
        return self

    def set_image_url(self, image_url: str) -> "SupplyBuilder":
        """Set a supply image_url."""
        self.supply.image_url = image_url
        return self

    def set_category(self, category: int) -> "SupplyBuilder":
        """Set a supply category."""
        if category is None:
            raise ValidationError({"category": [_("This field cannot be empty.")]})

        self.supply.category_id = category
        return self

    def set_unit_of_measure(self, unit_of_measure: int) -> "SupplyBuilder":
        """Set a supply unit_of_measure."""
        if unit_of_measure is None:
            raise ValidationError({"unit_of_measure": [_("This field cannot be empty.")]})

        self.supply.unit_of_measure_id = unit_of_measure
        return self

    def set_active(self, is_active: bool = True) -> "SupplyBuilder":
        """Set supply active status."""
        self.supply.is_active = is_active
        return self

    def build(self) -> Supply:
        """Build and return a supply instance."""
        # self.supply.full_clean()
        self.supply.save()
        return self.supply
