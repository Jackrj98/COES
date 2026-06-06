from crispy_forms.helper import FormHelper
from django import forms
from django.forms import modelformset_factory
from django.utils.translation import gettext_lazy as _

from apps.core.forms import BaseFilterForm, BaseFormHelperMixin
from apps.inventory.models import Supply
from apps.operations.models import ExitDetail, ExitOrder, PurchaseOrder


class PurchaseOrderBase(forms.ModelForm):
    """Form base for PurchaseOrder."""

    class Meta:
        model = PurchaseOrder
        fields = [
            "supplier",
            "observations",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_errors = True
        self.helper.error_text_inline = True
        self.helper.label_class = "form-label"
        self.helper.form_class = "needs-validation"


class ExitOrderBaseForm(forms.ModelForm):
    """Form base for ExitOrder."""

    class Meta:
        model = ExitOrder
        fields = [
            "motive",
            "observations",
        ]
        widgets = {
            "motive": forms.TextInput(
                attrs={
                    "class": "form-control datalist-input",
                    "list": "motive-list",
                }
            ),
            "observations": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Ej: Observaciones",
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


class ExitOrderDetailBaseForm(forms.ModelForm):
    """Form base for ExitDetail."""

    supply = forms.ModelChoiceField(
        queryset=Supply.objects.all(),
        to_field_name="code",
        widget=forms.Select(attrs={"class": "form-control"}),
        error_messages={"invalid_choice": "El insumo seleccionado no existe."},
    )

    class Meta:
        model = ExitDetail
        fields = ["quantity_requested", "supply"]
        widgets = {
            "quantity_requested": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "pattern": "[1-9][0-9]*",
                    "oninput": "this.value = this.value.replace(/^0+/, '')",  # JS básico inline
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


ExitOrderDetailFormSet = modelformset_factory(
    ExitDetail, form=ExitOrderDetailBaseForm, extra=0, can_delete=True, max_num=15
)


class ExitOrderFilterForm(BaseFilterForm, BaseFormHelperMixin):
    status = forms.ChoiceField(
        label=_("Status"),
        required=False,
        choices=BaseFilterForm.DEFAULT_CHOICE + list(ExitOrder.Status.choices),  # noqa
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        search_text = _("Search by order number or requested")
        if "search" in self.fields:
            self.fields["search"].widget.attrs.update(
                {"placeholder": search_text, "class": "form-control"}
            )

        self.setup_form_helper(
            label_class="form-label text-sm text-muted", form_class="needs-validation"
        )
