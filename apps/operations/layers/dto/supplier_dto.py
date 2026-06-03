from pydantic import BaseModel, EmailStr, Field, field_validator

from apps.security.utils.validators import validate_ecuadorian_id_or_ruc


class SupplierDTO(BaseModel):
    business_name: str = Field(..., min_length=3, max_length=200)
    contact_name: str = Field(..., min_length=3, max_length=255)
    tax_id: str = Field(..., min_length=10, max_length=13)
    delivery_days: int = Field(default=0)
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=15)
    address: str = Field(default="", max_length=255)

    @field_validator("tax_id")
    @classmethod
    def validate_document(cls, v: str) -> str:
        return validate_ecuadorian_id_or_ruc(v)
