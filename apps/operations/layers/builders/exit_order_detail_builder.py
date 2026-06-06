from decimal import Decimal

from apps.operations.models import ExitDetail


class ExitDetailBuilder:
    def __init__(self, detail=None):
        self.detail = detail or ExitDetail()

    def set_order(self, order_id: int):
        self.detail.exit_order_id = order_id
        return self

    def set_batch(self, batch_id: int):
        self.detail.batch_id = batch_id
        return self

    def set_supply(self, supply_id: int):
        self.detail.supply_id = supply_id
        return self

    def set_quantity_requested(self, qty: int) -> "ExitDetailBuilder":
        self.detail.quantity_requested = qty
        return self

    def set_quantity_received(self, qty: int) -> "ExitDetailBuilder":
        self.detail.quantity_received = qty
        return self

    def set_unit_cost(self, cost: Decimal) -> "ExitDetailBuilder":
        self.detail.unit_cost = Decimal(str(cost))
        return self

    def save(self):
        self.detail.save()
        return self

    def build(self) -> ExitDetail:
        return self.detail
