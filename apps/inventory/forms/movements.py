from crispy_forms.helper import FormHelper
from django import forms
from django.forms import modelformset_factory
from django.utils.translation import gettext_lazy as _

from apps.core.forms import BaseFilterForm, BaseFormHelperMixin
from apps.inventory.models import Batch, InventoryMovement


class InventoryMovementBaseForm(forms.ModelForm):
    """Form base for InventoryMovement."""

    class Meta:
        model = InventoryMovement
        fields = [
            "concept",
            "observation",
            "movement_type",
        ]
        widgets = {
            "concept": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "list": "concept-list",  # Conecta con el datalist
                    "placeholder": "Seleccione o escriba un concepto...",
                }
            ),
            "movement_type": forms.HiddenInput(attrs={"class": "form-control", "readonly": True}),
            "observation": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_errors = True
        self.helper.error_text_inline = True
        self.helper.label_class = "form-label"
        self.helper.form_class = "needs-validation"


class InventoryMovementForm(forms.ModelForm):
    supply = forms.ChoiceField(
        label=_("Supply"),
        widget=forms.Select(
            attrs={"class": "form-select select2", "data-placeholder": "Seleccione un insumo"}
        ),
        required=True,
    )
    batch = forms.ModelChoiceField(
        queryset=Batch.objects.none(),  # Se llena dinámicamente
        label=_("Batch"),
        widget=forms.Select(
            attrs={"class": "form-select select2", "data-placeholder": "Seleccione un lote"}
        ),
        required=True,
    )

    class Meta:
        model = InventoryMovement
        fields = ["supply", "batch", "quantity", "concept", "observation"]
        widgets = {
            "quantity": forms.NumberInput(
                attrs={"class": "form-control", "min": 1, "placeholder": "Cantidad"}
            ),
            "concept": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Motivo del movimiento"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_errors = True
        self.helper.error_text_inline = True
        self.helper.label_class = "form-label"

    # self.fields["supply"].choices = SupplyAppService().retrieve_active_choices()


# Formset
MovementFormSet = modelformset_factory(
    InventoryMovement, form=InventoryMovementForm, extra=1, can_delete=True, max_num=15
)

# ---------------------------------------------------------------------
# -----------------------FILTER FORMS----------------------------------
# ---------------------------------------------------------------------


class InventoryMovementFilterForm(BaseFilterForm, BaseFormHelperMixin):
    movement_type = forms.ChoiceField(
        label=_("Type"),
        required=False,
        choices=[("", _("All"))] + list(InventoryMovement.Type.choices),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    status = forms.ChoiceField(
        label=_("Status"),
        required=False,
        choices=[("", _("All"))] + list(InventoryMovement.MovementStatusChoices.choices),
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        search_text = _("Search by item, batch, or supply")
        if "search" in self.fields:
            self.fields["search"].widget.attrs.update(
                {"placeholder": search_text, "class": "form-control"}
            )

        self.setup_form_helper(
            label_class="form-label text-sm text-muted", form_class="needs-validation"
        )
