from crispy_forms.helper import FormHelper
from django import forms
from django.utils.translation import gettext_lazy as _

from apps.core.forms import BaseFilterForm, BaseFormHelperMixin
from apps.operations.models import Supplier


class SupplierFilterForm(BaseFilterForm, BaseFormHelperMixin):
    status = forms.ChoiceField(
        label=_("Status"),
        required=False,
        choices=BaseFilterForm.DEFAULT_CHOICE + list(Supplier.IsActiveChoices.choices),  # noqa
        widget=forms.Select(attrs={"class": "form-select"}),
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


class SupplierBaseForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = [
            "first_name",
            "last_name",
            "document_number",
            "business_name",
            "delivery_days",
            "email",
            "phone",
            "address",
        ]
        widgets = {
            "first_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej: Jon Doe"}
            ),
            "last_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: Doe"}),
            "document_number": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej: 1234567890", "maxlength": "13"}
            ),
            "business_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej: S.A.S. S.A."}
            ),
            "delivery_days": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "Ej: "}),
            "phone": forms.TelInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "+593 99 999 9999",
                    "pattern": r"\+?[0-9\s\-]+",
                }
            ),
            "address": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "placeholder": "Ej: Calle 123"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_errors = True
        self.helper.error_text_inline = True
        self.helper.label_class = "form-label"
        self.helper.form_class = "needs-validation"
