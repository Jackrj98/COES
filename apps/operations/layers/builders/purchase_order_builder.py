from apps.operations.management.management import OrderNumberGenerator
from apps.operations.models import PurchaseOrder


class PurchaseOrderBuilder:
    def __init__(self, purchase_order=None):
        self.order = purchase_order or PurchaseOrder()
        self._is_new = purchase_order is None

    def set_motive(self, motive: str) -> "PurchaseOrderBuilder":
        if motive:
            self.order.motive = motive.strip().capitalize()
        return self

    def set_observations(self, observations: str) -> "PurchaseOrderBuilder":
        if observations:
            self.order.observations = observations.strip().capitalize()
        return self

    def set_status(self, status: int) -> "PurchaseOrderBuilder":
        if status in PurchaseOrder.Status.values:
            self.order.status = status
        return self

    def set_supplier(self, supplier) -> "PurchaseOrderBuilder":
        self.order.supplier_id = supplier
        return self

    def set_estimated_delivery(self, delivery_date) -> "PurchaseOrderBuilder":
        self.order.estimated_delivery = delivery_date
        return self

    def set_actual_delivery(self, actual_delivery) -> "PurchaseOrderBuilder":
        self.order.actual_delivery = actual_delivery
        return self

    def build(self, save=True) -> PurchaseOrder:
        if self._is_new and not self.order.order_number:
            self.order.order_number = OrderNumberGenerator.generate(PurchaseOrder)

        if save:
            self.order.save()

        return self.order
