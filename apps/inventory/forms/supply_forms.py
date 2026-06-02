from crispy_forms.helper import FormHelper
from django import forms
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _

from apps.catalogs.layers.applications import CatalogItemAppService
from apps.catalogs.models import CatalogItem
from apps.core.forms import BaseFilterForm, BaseFormHelperMixin
from apps.inventory.models import Batch, InventoryMovement, Supply


class SupplyBaseForm(forms.ModelForm):
    """Form base for Supply."""

    category = forms.ModelChoiceField(
        label=_("Category"),
        queryset=CatalogItem.objects.none(),
        widget=forms.Select(attrs={"class": "form-select select2"}),
        empty_label=_("Select category"),
        required=True,
    )

    unit_of_measure = forms.ModelChoiceField(
        label=_("Unit of Measure"),
        queryset=CatalogItem.objects.none(),
        widget=forms.Select(attrs={"class": "form-select select2"}),
        empty_label=_("Select unit of measure"),
        required=True,
    )

    class Meta:
        model = Supply
        fields = [
            "name",
            "description",
            "image_url",
            "stock_min",
            "category",
            "unit_of_measure",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej: Amoxicilina 500mg"}
            ),
            "description": forms.Textarea(
                attrs={
                    "rows": 3,
                    "class": "form-control",
                    "required": False,
                    "placeholder": "Ej: Amoxicilina 500mg",
                }
            ),
            "image_url": forms.ClearableFileInput(
                attrs={
                    "class": "form-control image-preview-filepond",
                    "name": "image_url",
                    "accept": "image/*",
                }
            ),
            "stock_min": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input", "role": "switch"}),
        }
        validators = {
            "stock_min": [MinValueValidator(0)],
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_errors = True
        self.helper.error_text_inline = True
        self.helper.label_class = "form-label"
        self.helper.form_class = "needs-validation"

        service = CatalogItemAppService()
        self.fields["category"].queryset = (  # noqa
            service.retrieve_catalog_items(catalog_code="cat_supply")
            .only("id", "name", "code", "extra")
            .order_by("name")
        )
        self.fields["category"].label_from_instance = lambda obj: obj.name  # noqa

        self.fields["unit_of_measure"].queryset = (  # noqa
            service.retrieve_catalog_items(catalog_code="uni_measure")
            .only("id", "name", "extra")
            .order_by("name")
        )
        self.fields["unit_of_measure"].label_from_instance = lambda obj: (  # noqa
            f"{obj.name} ({obj.extra})" if obj.extra else obj.name
        )

    def get_service_payload(self):
        data = self.cleaned_data.copy()

        data.pop("image_url", None)

        category = data.pop("category", None)
        unit_of_measure = data.pop("unit_of_measure", None)

        if category:
            data["category_id"] = category.id
            data["category_code"] = category.extra

        if unit_of_measure:
            data["unit_of_measure_id"] = unit_of_measure.id

        return data


class BatchBaseForm(forms.ModelForm):
    """Form base for Batch."""

    class Meta:
        model = Batch
        fields = [
            "number",
            "due_date",
            "stock",
            "purchase_unit_cost",
            "status",
            "purchase_order",
        ]
        widgets = {
            "number": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej: LOTE-2026-001"}
            ),
            "due_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}, format="%Y-%m-%d"
            ),
            "stock": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "purchase_unit_cost": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0.01",
                    "type": "number",
                    "placeholder": "Ej: 12.50",
                }
            ),
            "purchase_order": forms.Select(attrs={"class": "form-select select2"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }
        validators = {
            "stock": [MinValueValidator(0)],
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_errors = True
        self.helper.error_text_inline = True
        self.helper.label_class = "form-label"
        self.helper.form_class = "needs-validation"

    def get_service_payload(self):
        data = self.cleaned_data.copy()

        purchase_order = data.pop("purchase_order", None)
        if purchase_order:
            data["purchase_order_id"] = purchase_order.id
        return data


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
        ]
        widgets = {
            "batch": forms.Select(attrs={"class": "form-select"}),
            "movement_type": forms.Select(attrs={"class": "form-select"}),
            "concept": forms.TextInput(attrs={"class": "form-control"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "observation": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "previous_stock": forms.NumberInput(attrs={"class": "form-control", "readonly": True}),
            "after_stock": forms.NumberInput(attrs={"class": "form-control", "readonly": True}),
        }
        validators = {
            "quantity": [MinValueValidator(0)],
            "previous_stock": [MinValueValidator(0)],
            "after_stock": [MinValueValidator(0)],
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_errors = True
        self.helper.error_text_inline = True
        self.helper.label_class = "form-label"
        self.helper.form_class = "needs-validation"


# ---------------------------------------------------------------------
# -----------------------FILTER FORMS----------------------------------
# ---------------------------------------------------------------------


class SupplyFilterForm(BaseFilterForm, BaseFormHelperMixin):
    category = forms.ChoiceField(
        label=_("Category"),
        required=False,
        widget=forms.Select(attrs={"class": "form-select select2"}),
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

    @staticmethod
    def generate_categories():
        queryset = CatalogItemAppService().retrieve_catalog_items(catalog_code="cat_supply")

        choices = [("", _("All categories"))]
        choices.extend([(item.code, item.name) for item in queryset])

        return choices


class BatchFilterForm(BaseFilterForm, BaseFormHelperMixin):
    status = forms.ChoiceField(
        label=_("Status"),
        required=False,
        choices=[("", _("All"))] + list(Batch.IsActiveChoices.choices),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    expiration = forms.ChoiceField(
        label=_("Expiration"),
        choices=[
            ("", _("All")),
            ("current", _("Current")),
            ("expiring", _("Expiring")),
            ("expired", _("Expired")),
        ],
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        search_text = _("Search by batch number")
        if "search" in self.fields:
            self.fields["search"].widget.attrs.update(
                {"placeholder": search_text, "class": "form-control"}
            )

        self.setup_form_helper(
            label_class="form-label text-sm text-muted", form_class="needs-validation"
        )


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
        choices=[("", _("All"))] + list(InventoryMovement.Status.choices),
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
