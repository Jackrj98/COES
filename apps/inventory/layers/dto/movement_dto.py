from decimal import Decimal

from pydantic import BaseModel, Field

from apps.inventory.models import InventoryMovement


class MovementDTO(BaseModel):
    batch_id: int = Field(..., ge=1)

    # Basic information
    quantity: int = Field(..., ge=0)
    movement_type: InventoryMovement.Type
    observation: str = Field(..., max_length=255)
    concept: str = Field(..., min_length=1, max_length=255)
    status: InventoryMovement.MovementStatusChoices = (
        InventoryMovement.MovementStatusChoices.COMPLETED
    )

    # Tracking
    previous_stock: int = Field(default=0, ge=0)
    after_stock: int = Field(default=0, ge=0)
    unit_cost_at_movement: Decimal = Field(default=0, ge=0)
    movement_date: str = Field(default=None)

    class Config:
        from_attributes = True
        str_strip_whitespace = True
        validate_assignment = True
        extra = "forbid"
