import re

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

text_only = RegexValidator(
    regex=r"^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$",
    message=_("Only upper letters, and underscores are allowed."),
    code="invalid_text_only",
)


def validate_ecuadorian_id_or_ruc(value: str) -> str:
    clean_id = re.sub(r"[\s\-]", "", value)

    if len(clean_id) not in [10, 13]:
        raise ValueError(_("The document must have 10 or 13 digits."))
    if not clean_id.isdigit():
        raise ValueError(_("The document must contain only numbers."))

    third_digit = int(clean_id[2])

    # 1. NATURAL PERSONS (0-5)
    if third_digit < 6:
        # Validation: Must be 10 digits or a natural person RUC (10 + 001)
        if len(clean_id) == 13 and not clean_id.endswith("001"):
            raise ValueError(_("Natural person RUC must end in 001."))

        base = clean_id[:10]
        digits = [int(d) for d in base]
        coeffs = [2, 1, 2, 1, 2, 1, 2, 1, 2]
        # Modulo 10 algorithm
        sum_ = sum(d * c if d * c < 10 else d * c - 9 for d, c in zip(digits[:9], coeffs))
        mod = sum_ % 10
        check = 0 if mod == 0 else 10 - mod
        if check != digits[9]:
            raise ValueError(_("Invalid ID/RUC number."))

    # 2. PRIVATE COMPANIES (9)
    elif third_digit == 9:
        if len(clean_id) != 13:
            raise ValueError(_("Private company RUC must have 13 digits."))
        digits = [int(d) for d in clean_id[:10]]
        coeffs = [4, 3, 2, 7, 6, 5, 4, 3, 2]
        sum_ = sum(d * c for d, c in zip(digits, coeffs))
        mod = sum_ % 11
        check = 0 if mod == 0 else (11 - mod)
        if check != digits[9]:
            raise ValueError(_("Invalid private company RUC."))

    # 3. PUBLIC ENTITIES (6)
    elif third_digit == 6:
        if len(clean_id) != 13:
            raise ValueError(_("Public entity RUC must have 13 digits."))
        digits = [int(d) for d in clean_id[:9]]
        coeffs = [3, 2, 7, 6, 5, 4, 3, 2]
        sum_ = sum(d * c for d, c in zip(digits, coeffs))
        mod = sum_ % 11
        check = 0 if mod == 0 else (11 - mod)
        if check != digits[8]:
            raise ValueError(_("Invalid public entity RUC."))

    else:
        raise ValueError(_("Invalid third digit."))

    return clean_id


def django_id_validator(value: str):
    try:
        validate_ecuadorian_id_or_ruc(value)
    except ValueError as e:
        raise DjangoValidationError(str(e))
