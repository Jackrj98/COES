from datetime import date

from pydantic import BaseModel, Field, field_validator


class BatchDTO(BaseModel):
    number: str = Field(..., min_length=3, max_length=100)
    due_date: date
    stock: int = Field(default=0, ge=0)
    purchase_unit_cost: float = Field(..., ge=0.0)
    is_active: bool = Field(default=True)
    status: int = Field(default=1, ge=0, le=2)
    purchase_order_id: int | None = Field(None, ge=1)
    supply_id: int = Field(..., ge=1)

    class Config:
        from_attributes = True
        str_strip_whitespace = True
        validate_assignment = True
        extra = "forbid"

    @field_validator("due_date", mode="before", check_fields=False)
    @classmethod
    def validate_due_date(cls, value):
        """Validate that the due date is not in the past."""
        if value < date.today():
            raise ValueError(f"Due date must be today or in the future. Got: {value}")
        return value
