from pydantic import BaseModel, Field


class SupplyDTO(BaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    code: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern=r"^[A-Z0-9_-]+$",
    )
    description: str = Field(default="", max_length=255)
    image_url: str | None = Field(None)
    stock_min: int = Field(default=10, ge=0)
    is_active: bool = Field(default=True)
    category_id: int = Field(..., ge=1)
    unit_of_measure_id: int = Field(..., ge=1)

    class Config:
        from_attributes = True
        str_strip_whitespace = True
        validate_assignment = True
        extra = "forbid"
