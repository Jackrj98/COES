from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class PurchaseOrderDetailDTO(BaseModel):
    supply_id: int = Field(..., gt=0)
    quantity_requested: int = Field(..., gt=0)
    quantity_received: int = Field(default=0, ge=0)
    unit_cost: Decimal = Field(default=Decimal("0.00"))
    observations: str = Field(default="")

    class Config:
        from_attributes = True


class PurchaseOrderDTO(BaseModel):
    status: int = Field(default=0)
    motive: str = Field(default="", max_length=500)
    observations: str = Field(default="", max_length=500)
    estimated_delivery: date
    actual_delivery: date
    supplier_id: int = Field(..., gt=0)

    details: list[PurchaseOrderDetailDTO] = Field(..., min_length=1)

    class Config:
        from_attributes = True
