from django.db import models
from django.utils.translation import gettext_lazy as _


class InventoryMovementType(models.IntegerChoices):
    INBOUND = 0, _("Inbound")
    OUTBOUND = 1, _("Outbound")
    ADJUSTMENT = 2, _("Adjustment")

    @property
    def style(self):
        configs = {
            self.INBOUND.value: {"color": "success", "icon": "bi bi-arrow-up"},
            self.OUTBOUND.value: {"color": "danger", "icon": "bi bi-arrow-down"},
            self.ADJUSTMENT.value: {"color": "primary", "icon": "bi bi-plus-lg"},
        }
        return configs[self.value]

    @property
    def color(self) -> str:
        return self.style["color"]

    @property
    def icon(self) -> str:
        return self.style["icon"]

    @classmethod
    def get_ui_map(cls):
        return {
            item.value: {"color": item.color, "icon": item.icon, "label": item.label}
            for item in cls
        }


class InventoryMovementStatus(models.IntegerChoices):
    PENDING = 0, _("Pending")
    COMPLETED = 1, _("Completed")
    CANCELLED = 2, _("Cancelled")

    @property
    def style(self):
        configs = {
            self.PENDING.value: {"color": "warning"},
            self.COMPLETED.value: {"color": "success"},
            self.CANCELLED.value: {"color": "secondary"},
        }
        return configs[self.value]

    @property
    def color(self) -> str:
        return self.style["color"]

    @classmethod
    def get_ui_map(cls):
        return {item.value: {"color": item.color, "label": item.label} for item in cls}
