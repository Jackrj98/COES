from django.utils.translation import gettext_lazy as _
from pydantic import BaseModel, Field, field_validator


class CatalogDTO(BaseModel):
    """DTO for Catalog model."""

    name: str = Field(..., min_length=3, max_length=255)
    code: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_]+$",
        description=str(_("Unique identifier code, numbers and underscores")),
    )
    description: str = Field(max_length=1000)
    priority: int = Field(default=100, ge=1, le=10000)
    is_active: bool = Field(default=True)

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        """Validate a code format."""
        if not v.replace("_", "").isalnum():
            raise ValueError(_("Code can only contain letters, numbers and underscores"))
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name."""
        if not v.strip():
            raise ValueError(_("Name cannot be empty or only whitespace"))
        return v.strip()

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: int) -> int:
        """Validate priority range."""
        if v < 1 or v > 10000:
            raise ValueError(_("Priority must be between 1 and 100000"))
        return v

    class Config:
        str_strip_whitespace = True
        validate_assignment = True
        extra = "forbid"


class CatalogItemDTO(BaseModel):
    """DTO for CatalogItem model."""

    name: str = Field(..., min_length=3, max_length=255)
    code: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_]+$",
        description=str(_("Unique identifier code, numbers and underscores")),
    )
    description: str = Field(default="", max_length=1000)
    priority: int = Field(default=100, ge=1, le=10000)
    extra: str = Field(default="", max_length=100)
    catalog_id: int = Field(..., gt=0)
    is_active: bool = Field(default=True)

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        """Validate a code format."""
        if not v.replace("_", "").isalnum():
            raise ValueError(_("Code can only contain uppercase letters, numbers and underscores"))
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name."""
        if not v.strip():
            raise ValueError(_("Name cannot be empty or only whitespace"))
        return v.strip()

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: int) -> int:
        """Validate priority range."""
        if v < 1 or v > 10000:
            raise ValueError(_("Priority must be between 1 and 10000"))
        return v

    class Config:
        str_strip_whitespace = True
        validate_assignment = True
        extra = "forbid"
