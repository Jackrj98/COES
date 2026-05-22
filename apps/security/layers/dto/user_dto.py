import re

from django.utils.translation import gettext_lazy as _
from pydantic import BaseModel, Field, field_validator


class UserRegistrationDTO(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=3, max_length=75)
    last_name: str = Field(..., min_length=3, max_length=75)
    document_number: str = Field(..., min_length=10, max_length=13)
    phone: str = Field(..., min_length=13, max_length=13)
    groups: list[str] = Field(default_factory=list)

    @field_validator("document_number", mode="after")
    @classmethod
    def validate_document(cls, value: str) -> str:
        # 1. Clean spaces and hyphens
        clean_id = re.sub(r"[\s\-]", "", value)

        # 2. Verify it contains exactly 10 numeric digits
        if not clean_id.isdigit() or len(clean_id) != 10:
            raise ValueError(_("The ID card must contain exactly 10 numeric digits."))

        # 3. Validate province code (first two digits)
        province = int(clean_id[0:2])
        if not (1 <= province <= 24 or province == 30):
            raise ValueError(_("The province code of the ID card is invalid."))

        # 4. Validate the third digit (must be less than 6 for regular ID cards)
        third_digit = int(clean_id[2])
        if third_digit >= 6:
            raise ValueError(_("The entered document does not match a valid ID card."))

        # 5. Luhn / Modulo 10 Algorithm (Check digit)
        digits = [int(d) for d in clean_id]
        provided_check_digit = digits[9]

        # Coefficients set by the Civil Registry of Ecuador
        coefficients = [2, 1, 2, 1, 2, 1, 2, 1, 2]
        total_sum = 0

        for i in range(9):
            product = digits[i] * coefficients[i]
            if product >= 10:
                product -= 9
            total_sum += product

        modulo_remainder = total_sum % 10

        if modulo_remainder == 0:
            calculated_check_digit = 0
        else:
            calculated_check_digit = 10 - modulo_remainder

        # 6. Compare check digits
        if calculated_check_digit != provided_check_digit:
            raise ValueError(_("The ID number you entered is invalid."))

        return clean_id


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
