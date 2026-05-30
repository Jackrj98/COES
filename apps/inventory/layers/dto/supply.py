from django.utils.translation import gettext_lazy as _
from pydantic import BaseModel, Field, field_validator


class SupplyDTO(BaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    code: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern=r"^[A-Z0-9_]+$",
    )
    description: str = Field(default="", max_length=255)
    image_url: str = Field(default="")
    stock_min: int = Field(default=10, ge=0)
    is_active: bool = Field(default=True)
    category_id: int = Field(..., ge=1)
    unit_of_measure_id: int = Field(..., ge=1)

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        """Validate a code format."""
        if not v.replace("_", "").isalnum():
            raise ValueError(_("Code can only contain uppercase letters, numbers and underscores"))
        return v

    class Config:
        from_attributes = True
        str_strip_whitespace = True
        validate_assignment = True
        extra = "forbid"
