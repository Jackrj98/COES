from crispy_forms.helper import FormHelper
from django import forms
from django.utils.translation import gettext_lazy as _

from apps.catalogs.layers.applications import CatalogAppService
from apps.catalogs.models import Catalog, CatalogItem
from apps.core.forms import BaseFilterForm, BaseFormHelperMixin


class CatalogFilterForm(BaseFilterForm, BaseFormHelperMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        search_text = _("Search by name or code")
        if "search" in self.fields:
            self.fields["search"].widget.attrs.update(
                {"placeholder": search_text, "class": "form-control"}
            )

        self.setup_form_helper(
            label_class="form-label text-sm text-muted", form_class="needs-validation"
        )


class CatalogBaseForm(forms.ModelForm):
    class Meta:
        model = Catalog
        fields = ["name", "code", "description", "is_active", "priority"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej: Antibioticos"}
            ),
            "code": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: ALI"}),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "placeholder": "Ej:"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input", "role": "switch"}),
            "priority": forms.NumberInput(
                attrs={"class": "form-control", "min": 0, "type": "number"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_errors = True
        self.helper.error_text_inline = True
        self.helper.label_class = "form-label"
        self.helper.form_class = "needs-validation"

        service = CatalogAppService()
        self.fields["priority"].initial = service.generate_next_priority()


class CatalogItemBaseForm(forms.ModelForm):
    class Meta:
        model = CatalogItem
        fields = ["name", "code", "extra", "description", "is_active", "priority", "catalog"]
        widgets = {
            "catalog": forms.HiddenInput(attrs={"class": "form-control", "readonly": True}),
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej: Antibioticos"}
            ),
            "code": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: ALI"}),
            "extra": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: ALI"}),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "placeholder": "Ej:"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input", "role": "switch"}),
            "priority": forms.NumberInput(
                attrs={"class": "form-control", "min": 0, "type": "number"}
            ),
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_errors = True
        self.helper.error_text_inline = True
        self.helper.label_class = "form-label"
        self.helper.form_class = "needs-validation"
