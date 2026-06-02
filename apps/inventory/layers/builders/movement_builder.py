from decimal import Decimal

from apps.inventory.models import InventoryMovement


class InventoryMovementBuilder:
    def __init__(self, movement=None):
        self.movement = movement or InventoryMovement()

    def set_batch(self, batch_id) -> "InventoryMovementBuilder":
        if batch_id:
            self.movement.batch_id = batch_id
        return self

    def set_type(self, movement_type: int) -> "InventoryMovementBuilder":
        if movement_type in InventoryMovement.Type.values:
            self.movement.movement_type = movement_type
        return self

    def set_concept(self, concept: str) -> "InventoryMovementBuilder":
        if concept:
            self.movement.concept = concept.strip()[:255]
        return self

    def set_quantity(self, quantity: int) -> "InventoryMovementBuilder":
        if quantity is not None:
            self.movement.quantity = max(0, int(quantity))
        return self

    def set_observation(self, observation: str | None) -> "InventoryMovementBuilder":
        if observation:
            self.movement.observation = observation.strip()[:255]
        return self

    def set_stock_data(self, previous: int, after: int) -> "InventoryMovementBuilder":
        self.movement.previous_stock = max(0, int(previous))
        self.movement.after_stock = max(0, int(after))
        self.movement.is_increment = self.movement.after_stock > self.movement.previous_stock
        return self

    def set_unit_cost(self, cost: int | float | str | Decimal) -> "InventoryMovementBuilder":
        if cost is not None:
            self.movement.unit_cost_at_movement = Decimal(str(cost))
        return self

    def set_status(self, status: int) -> "InventoryMovementBuilder":
        if status in InventoryMovement.Status.values:
            self.movement.status = status
        return self

    def save(self) -> "InventoryMovementBuilder":
        self.movement.save()
        return self

    def build(self) -> InventoryMovement:
        return self.movement
