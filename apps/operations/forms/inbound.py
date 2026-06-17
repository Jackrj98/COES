from decimal import Decimal, InvalidOperation

from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Column, Layout, Row
from django import forms
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _

from apps.core.forms import BaseFilterForm, BaseFormHelperMixin
from apps.operations.models import InboundOrder, InventoryOrder, OrderDetail


class InboundOrderForm(forms.ModelForm):
    class Meta:
        model = InboundOrder
        fields = [
            "order_type",
            "status",
            "motive",
            "observations",
            "supplier",
            "scheduled_date",
            "received_date",
        ]
        widgets = {
            "supplier": forms.Select(attrs={"class": "form-control select2"}),
            "scheduled_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"
            ),
            "received_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"
            ),
            "motive": forms.TextInput(
                attrs={"class": "form-control datalist-input", "list": "inbound-list"}
            ),
            "order_type": forms.HiddenInput(attrs={"class": "form-control", "readonly": True}),
            "status": forms.Select(attrs={"class": "form-control"}),
            "observations": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "cols": 3,
                    "placeholder": "Ej: Observaciones",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.form_show_errors = True
        self.helper.error_text_inline = True
        self.helper.form_class = "needs-validation"
        self.helper.label_class = "form-label fw-medium"

        col_class = "col-12 col-md-4" if self.instance.pk else "col-12 col-md-6"
        self.helper.layout = Layout(
            Row(
                Column("order_type", css_class="col-12 col-md-6"),
            ),
            Row(
                Column("motive", css_class="col-12 col-md-6"),
                Column("supplier", css_class="col-12 col-md-6"),
            ),
            Row(
                Column("scheduled_date", css_class=col_class),
                Column("received_date", css_class=col_class) if self.instance.pk else HTML(""),
                Column("status", css_class=col_class),
            ),
            Row(
                Column("observations", css_class="col-12"),
            ),
        )

        self.fields["supplier"].required = True
        self.fields["order_type"].initial = InventoryOrder.OrderType.INBOUND.value
        self.fields["order_type"].widget = forms.HiddenInput()

        if not self.instance.pk:
            self.fields["status"].initial = InventoryOrder.StatusType.SENT
            self.fields["status"].required = False  #
            self.fields["status"].disabled = True
            self.fields["status"].widget.attrs["disabled"] = True

            self.fields["received_date"].widget = forms.HiddenInput()
            self.fields["received_date"].required = False

        if self.instance.pk:
            allowed_statuses = [
                InventoryOrder.StatusType.COMPLETED,
                InventoryOrder.StatusType.CANCELLED,
            ]
            self.fields["status"].choices = [
                choice for choice in self.fields["status"].choices if choice[0] in allowed_statuses
            ]


class InboundOrderDetailBaseForm(forms.ModelForm):
    batch_number = forms.CharField(
        label="",
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "LOTE #782",
            }
        ),
    )
    expiry_date = forms.DateField(
        label="",
        required=True,
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
            },
            format="%Y-%m-%d",
        ),
    )

    class Meta:
        model = OrderDetail
        fields = [
            "supply",
            "quantity_requested",
            "quantity_fulfilled",
            "unit_cost",
            "observations",
        ]
        widgets = {
            "supply": forms.Select(attrs={"class": "form-control"}),
            "quantity_requested": forms.NumberInput(attrs={"class": "form-control text-center"}),
            "quantity_fulfilled": forms.NumberInput(attrs={"class": "form-control text-center"}),
            "unit_cost": forms.NumberInput(
                attrs={"class": "form-control text-center", "step": "any"}
            ),
            "observations": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        self.order_type = kwargs.pop("order_type", None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_errors = True
        self.helper.error_text_inline = True
        self.helper.form_class = "needs-validation"
        self.helper.label_class = "form-label fw-medium"

        if not self.instance.pk:
            self.fields["quantity_fulfilled"].required = False

        for field in self.fields.values():
            field.label = ""

    def clean_unit_cost(self):
        unit_cost = self.cleaned_data.get("unit_cost")
        if unit_cost is None:
            return None

        try:
            cost = Decimal(str(unit_cost))
        except (InvalidOperation, ValueError, TypeError):
            raise ValidationError(_("Unit cost must be a number"))

        if cost <= 0:
            raise ValidationError(_("Unit cost must be greater than 0"))

        if cost > Decimal("999999.99"):
            raise ValidationError(_("Unit cost cannot be greater than 999,999.99"))

        return cost

    def clean(self):
        cleaned_data = super().clean()
        batch = cleaned_data.get("batch_number")
        supply = cleaned_data.get("supply")

        batches = supply.batches.filter(batch_number=batch)

        if self.instance.pk:
            batches = batches.exclude(id=self.instance.batch_id)
            if batches.exists():
                self.add_error("batch_number", _("Batch number already exists for this supply."))

        if batches.exists():
            self.add_error("batch_number", _("Batch number already exists for this supply."))

        return cleaned_data


InboundOrderDetailFormSet = inlineformset_factory(
    InventoryOrder,
    OrderDetail,
    extra=1,
    form=InboundOrderDetailBaseForm,
    can_delete=True,
    max_num=30,
)


class InboundOrderFilterForm(BaseFilterForm, BaseFormHelperMixin):
    status = forms.ChoiceField(
        label=_("Status"),
        required=False,
        choices=BaseFilterForm.DEFAULT_CHOICE + list(InboundOrder.StatusType.choices),  # noqa
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        search_text = _("Search by order number, requested, supplier")
        if "search" in self.fields:
            self.fields["search"].widget.attrs.update(
                {"placeholder": search_text, "class": "form-control"}
            )

        self.setup_form_helper(
            label_class="form-label text-sm text-muted", form_class="needs-validation"
        )
