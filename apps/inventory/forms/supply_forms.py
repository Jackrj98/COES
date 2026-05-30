from django import forms
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _

from apps.catalogs.layers.applications import CatalogItemAppService
from apps.core.forms import BaseFilterForm, BaseFormHelperMixin
from apps.inventory.models import Batch, InventoryMovement, Supply


class SupplyBaseForm(forms.ModelForm):
    """Form base for Supply."""

    class Meta:
        model = Supply
        fields = [
            "name",
            "code",
            "description",
            "image_url",
            "stock_min",
            "category",
            "unit_of_measure",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej: Amoxicilina 500mg"}
            ),
            "code": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: INS-001"}),
            "description": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "image_url": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "stock_min": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "category": forms.Select(attrs={"class": "form-select choices"}),
            "unit_of_measure": forms.Select(attrs={"class": "form-select choices"}),
        }
        validators = {
            "stock_min": [MinValueValidator(0)],
        }


class BatchBaseForm(forms.ModelForm):
    """Form base for Batch."""

    class Meta:
        model = Batch
        fields = ["supply", "number", "expiration_date", "stock", "purchase_unit_cost", "status"]
        widgets = {
            "supply": forms.Select(attrs={"class": "form-select"}),
            "number": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej: LOTE-2026-001"}
            ),
            "expiration_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}, format="%Y-%m-%d"
            ),
            "stock": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "purchase_unit_cost": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0.01"}
            ),
            "status": forms.Select(attrs={"class": "form-select"}),
        }
        validators = {
            "stock": [MinValueValidator(0)],
        }


class InventoryMovementBaseForm(forms.ModelForm):
    """Form base for InventoryMovement."""

    class Meta:
        model = InventoryMovement
        fields = [
            "batch",
            "movement_type",
            "concept",
            "quantity",
            "observation",
            "previous_stock",
            "after_stock",
            "is_increment",
        ]
        widgets = {
            "batch": forms.Select(attrs={"class": "form-select"}),
            "movement_type": forms.Select(attrs={"class": "form-select"}),
            "concept": forms.TextInput(attrs={"class": "form-control"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "observation": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "previous_stock": forms.NumberInput(attrs={"class": "form-control", "readonly": True}),
            "after_stock": forms.NumberInput(attrs={"class": "form-control", "readonly": True}),
            "is_increment": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        validators = {
            "quantity": [MinValueValidator(0)],
            "previous_stock": [MinValueValidator(0)],
            "after_stock": [MinValueValidator(0)],
        }


# ---------------------------------------------------------------------
# -----------------------FILTER FORMS----------------------------------
# ---------------------------------------------------------------------


class SupplyFilterForm(BaseFilterForm, BaseFormHelperMixin):
    category = forms.ChoiceField(
        label=_("Category"),
        required=False,
        widget=forms.Select(attrs={"class": "form-select choices"}),
    )
    stock = forms.ChoiceField(
        label=_("Stock"),
        choices=[
            ("", _("All stocks")),
            ("low", _("Low stock")),
            ("normal", _("Normal stock")),
            ("critical", _("Critical stock")),
        ],
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

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

        self.fields["category"].choices = self.generate_categories()

    def generate_categories(self):
        queryset = CatalogItemAppService().retrieve_catalog_items(catalog_code="cat_supply")

        choices = [("", _("All categories"))]
        choices.extend([(item.code, item.name) for item in queryset])

        return choices
