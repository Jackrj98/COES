from crispy_forms.helper import FormHelper
from django import forms
from django.utils.translation import gettext_lazy as _

from apps.core.forms import BaseFilterForm, BaseFormHelperMixin
from apps.purchasing.layers.applications import SupplierAppService
from apps.purchasing.models import Supplier


class SupplierFilterForm(BaseFilterForm, BaseFormHelperMixin):
    status = forms.ChoiceField(
        label=_("Status"),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    reason = forms.ChoiceField(
        label=_("Reasons"),
        required=False,
        widget=forms.Select(attrs={"class": "form-select choices"}),
    )
    delivery_days = forms.ChoiceField(
        label=_("Delivery days"),
        required=False,
        choices=[
            ("", _("All deadlines")),
            ("fast", _("Fast (≤ 5 days)")),
            ("medium", _("Medium (6–14 days)")),
            ("slow", _("Slow (> 14 days)")),
        ],
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        search_text = _("Search by name or ruc")
        if "search" in self.fields:
            self.fields["search"].widget.attrs.update(
                {"placeholder": search_text, "class": "form-control"}
            )

        self.setup_form_helper(
            label_class="form-label text-sm text-muted", form_class="needs-validation"
        )

        reason_choices = [("", _("All reasons"))] + SupplierAppService().retrieve_reasons()
        status_choices = BaseFilterForm.DEFAULT_CHOICE + list(Supplier.IsActiveChoices.choices)  # type: ignore
        self.fields["reason"].choices = reason_choices
        self.fields["status"].choices = status_choices


class SupplierBaseForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ["business_name", "reason", "delivery_days", "tax_id", "email", "phone"]
        widgets = {
            "business_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej: Be"}
            ),
            "reason": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "placeholder": "Ej:"}
            ),
            "delivery_days": forms.NumberInput(
                attrs={"class": "form-control", "min": 0, "type": "number"}
            ),
            "tax_id": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej: 1234567890"}
            ),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "Ej: "}),
            "phone": forms.TelInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "+593 99 999 9999",
                    "pattern": r"\+?[0-9\s\-]+",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_errors = True
        self.helper.error_text_inline = True
        self.helper.label_class = "form-label"
        self.helper.form_class = "needs-validation"
