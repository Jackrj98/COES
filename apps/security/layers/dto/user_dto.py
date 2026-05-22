from django.utils.translation import gettext_lazy as _
from pydantic import BaseModel, EmailStr, Field, field_validator

from apps.security.utils.validators import validate_ecuadorian_id_or_ruc


class BaseUserDTO(BaseModel):
    first_name: str = Field(..., min_length=3, max_length=75)
    last_name: str = Field(..., min_length=3, max_length=75)
    document_number: str = Field(..., min_length=10, max_length=13)
    phone: str = Field(..., min_length=10, max_length=15)

    @field_validator("document_number")
    @classmethod
    def validate_document(cls, v: str) -> str:
        return validate_ecuadorian_id_or_ruc(v)


class UserRegistrationDTO(BaseUserDTO):
    email: EmailStr
    username: str = Field(..., min_length=5, max_length=50)
    password: str = Field(..., min_length=8, max_length=50)
    groups: list[str] = Field(default_factory=list)


class UserPasswortDTO(BaseModel):
    user: object = Field(exclude=True)
    current_password: str = Field(..., min_length=5, max_length=50)
    new_password: str = Field(..., min_length=8, max_length=50)
    confirm_password: str = Field(..., min_length=8, max_length=50)

    @field_validator("confirm_password", mode="after")
    @classmethod
    def validate_passwords_match(cls, v, info):
        new_password = info.data.get("new_password")
        if new_password and v != new_password:
            raise ValueError(_("The passwords do not match."))
        return v

    @field_validator("new_password", mode="after")
    @classmethod
    def validate_new_not_same_as_current(cls, v, info):
        current = info.data.get("current_password")
        if current and v == current:
            raise ValueError(_("The new password cannot be the same as the current password."))
        return v

    @field_validator("current_password", mode="after")
    @classmethod
    def validate_current_password(cls, v, info):
        user = info.data.get("user")
        if user and not user.check_password(v):
            raise ValueError(_("The current password is incorrect."))
        return v
