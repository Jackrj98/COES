# builders/order_detail.py
from django.db import transaction

from apps.operations.models import OrderDetail


class OrderDetailBuilder:
    def __init__(self, order):
        self.order = order
        self.current_line = None
        self.lines = []

    def start_line(self, supply_id):
        self.current_line = OrderDetail(inventory_order=self.order, supply_id=supply_id)
        return self

    def set_unit_cost(self, unit_cost):
        self.current_line.unit_cost = unit_cost
        return self

    def set_requested_quantity(self, quantity):
        self.current_line.quantity_requested = quantity
        return self

    def set_fulfilled_quantity(self, quantity):
        self.current_line.quantity_fulfilled = quantity
        return self

    def set_batch(self, batch):
        self.current_line.batch = batch
        return self

    def set_observations(self, observations):
        self.current_line.observations = observations
        return self

    def finish_line(self):
        self.lines.append(self.current_line)
        self.current_line = None
        return self

    def save(self):
        if not self.lines:
            return []

        for idx, line in enumerate(self.lines):
            if line.pk:
                line.pk = None

        with transaction.atomic():
            from crum import get_current_user

            user = get_current_user()
            user_identifier = "system"

            if user and user.pk:
                user_identifier = getattr(user, "email", None) or str(user)

            for line in self.lines:
                line.inventory_order = self.order
                if not line.created_by:
                    line.created_by = user_identifier

            return OrderDetail.objects.bulk_create(self.lines)
