from datetime import date

from pydantic import BaseModel, Field, field_validator


class BatchDTO(BaseModel):
    batch_number: str = Field(..., min_length=3, max_length=100)
    expiry_date: date
    initial_quantity: int = Field(ge=1)
    current_quantity: int = Field(ge=0)
    unit_cost: float = Field(..., ge=0.0)
    is_active: bool = Field(default=True)
    status: int = Field(default=1, ge=0, le=2)
    supply_id: int = Field(..., ge=1)

    class Config:
        from_attributes = True
        str_strip_whitespace = True
        validate_assignment = True
        extra = "forbid"

    @field_validator("expiry_date", mode="before", check_fields=False)
    @classmethod
    def validate_expiry_date(cls, value):
        """Validate that the expiry date is not in the past."""
        if value < date.today():
            raise ValueError(f"Expiry date must be today or in the future. Got: {value}")
        return value
