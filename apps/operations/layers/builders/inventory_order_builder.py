from django.core.exceptions import ValidationError

from apps.operations.management.management import OrderNumberGenerator
from apps.operations.models import InventoryOrder


class InventoryOrderBuilder:
    def __init__(self, order):
        self.order = order

    def set_order_type(self, order_type: int):
        if order_type not in InventoryOrder.OrderType.values:
            raise ValidationError({"order_type": "Invalid order type"})

        self.order.order_type = order_type
        return self

    def set_motive(self, motive: str):
        if not motive or not isinstance(motive, str):
            raise ValidationError({"motive": "Motive is required"})

        self.order.motive = motive.strip().capitalize()
        return self

    def set_observations(self, observations: str):
        self.order.observations = observations
        return self

    def set_scheduled_date(self, date):
        if not date:
            raise ValidationError({"scheduled_date": "Scheduled date is required"})

        self.order.scheduled_date = date
        return self

    def set_received_date(self, date):
        if not date:
            raise ValidationError({"received_date": "Received date is required"})

        self.order.received_date = date
        return self

    def set_status(self, status):
        if status not in InventoryOrder.StatusType.values:
            raise ValidationError({"status": "Invalid status"})

        self.order.status = status
        return self

    def set_supplier(self, supplier_id):
        if not supplier_id:
            raise ValidationError({"supplier": "Supplier is required"})

        self.order.supplier_id = supplier_id
        return self

    def build(self):
        self.order.order_number = OrderNumberGenerator.generate(self.order.__class__)
        self.order.full_clean()
        self.order.save()
        return self.order
