from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class ExitDetailDTO(BaseModel):
    supply_id: int = Field(..., gt=0)
    batch_id: int | None = None
    quantity_requested: int = Field(..., gt=1)
    quantity_dispatched: int = Field(default=0, ge=0)
    unit_cost: Decimal = Field(default=Decimal("0.00"), decimal_places=2)

    @field_validator("quantity_dispatched")
    @classmethod
    def validate_quantity(cls, v, info):
        if v > info.data.get("quantity_requested", 0):
            raise ValueError(
                f"Quantity dispatched ({v}) cannot exceed quantity requested ({info.data.get('quantity_requested')})"
            )
        return v


class ExitOrderDTO(BaseModel):
    status: int = Field(default=0, ge=0, le=2)

    requested_by: str = Field(..., min_length=3, max_length=255)

    observations: str = Field(default="", max_length=500)
    motive: str = Field(default="", max_length=500)
    subtotal: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)

    total: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)

    details: list["ExitDetailDTO"] = Field(..., min_length=1)

    @field_validator("total")
    @classmethod
    def validate_total(cls, v, info):
        subtotal = info.data.get("subtotal", Decimal("0.00"))
        if v != subtotal:
            raise ValueError(f"El total ({v}) debe ser igual al subtotal ({subtotal})")
        return v

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True
