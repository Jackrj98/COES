from apps.operations.management.management import OrderNumberGenerator
from apps.operations.models import ExitDetail, ExitOrder


class ExitOrderBuilder:
    def __init__(self, exit_order=None):
        self.exit_order = exit_order or ExitOrder()

    def set_status(self, status: int) -> "ExitOrderBuilder":
        if status in self.exit_order.Status:
            self.exit_order.status = status
        return self

    def requested_by(self, requested_by: str) -> "ExitOrderBuilder":
        self.exit_order.requested_by = requested_by.strip().lower()
        return self

    def set_observations(self, observations: str) -> "ExitOrderBuilder":
        self.exit_order.observations = observations.strip().capitalize()
        return self

    def set_motive(self, motive: str) -> "ExitOrderBuilder":
        self.exit_order.motive = motive.strip().capitalize()
        return self

    def set_subtotal(self, subtotal: float) -> "ExitOrderBuilder":
        self.exit_order.subtotal = subtotal
        return self

    def set_total(self, total: float) -> "ExitOrderBuilder":
        self.exit_order.total = total
        return self

    def add_detail(self, supply, quantity: float, price: float) -> "ExitOrderBuilder":
        detail = ExitDetail(
            exit_order=self.exit_order, supply=supply, quantity=quantity, unit_price=price
        )
        if not hasattr(self, "_details"):
            self._details = []  # noqa
        self._details.append(detail)
        return self

    def save(self):
        self.exit_order.order_number = OrderNumberGenerator.generate(ExitOrder)
        self.exit_order.save()
        return self

    def build(self):
        return self.exit_order
