from crispy_forms.helper import FormHelper
from django import forms
from django.utils.translation import gettext_lazy as _


class BaseFormHelperMixin:
    """Mixin to configure Crispy Forms helper consistently."""

    def setup_form_helper(self, label_class="form-label", form_class="needs-validation"):
        """Configure the Crispy Forms helper."""
        self.helper = FormHelper()
        self.helper.form_show_errors = True
        self.helper.error_text_inline = True
        self.helper.label_class = label_class
        self.helper.form_class = form_class


class BaseFilterForm(forms.Form, BaseFormHelperMixin):
    DEFAULT_CHOICE = [("", _("Select"))]

    search = forms.CharField(
        label=_("Search"),
        required=False,
        widget=forms.TextInput(
            attrs={
                "type": "search",
                "placeholder": _("Search by params"),
            }
        ),
    )
    date_from = forms.DateField(
        label=_("Date"),
        required=False,
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "flatpickr-range",
                "min": "2000-01-01",
                "max": "2100-01-01",
                "placeholder": _("Select date"),
            },
            format="%Y-%m-%d",
        ),
    )
    status = forms.ChoiceField(
        label=_("Status"),
        required=False,
        choices=[("", _("Select")), (1, _("Active")), (0, _("Inactive"))],
        widget=forms.Select(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setup_form_helper()
