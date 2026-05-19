from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

text_only = RegexValidator(
    regex=r"^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$",
    message=_("Only upper letters, and underscores are allowed."),
    code="invalid_text_only",
)
