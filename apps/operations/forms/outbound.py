from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Layout, Row
from django import forms
from django.forms import inlineformset_factory

from apps.inventory.models import Supply
from apps.operations.models import InventoryOrder, OrderDetail, OutboundOrder


class OutboundOrderForm(forms.ModelForm):
    class Meta:
        model = OutboundOrder
        fields = ["order_type", "status", "motive", "observations"]
        widgets = {
            "motive": forms.TextInput(
                attrs={"class": "form-control datalist-input", "list": "outbound-list"}
            ),
            "order_type": forms.HiddenInput(attrs={"class": "form-control", "readonly": True}),
            "status": forms.HiddenInput(attrs={"class": "form-control", "readonly": True}),
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

        self.helper.layout = Layout(
            Row(
                Column("order_type", css_class="col-12 col-md-6"),
                Column("status", css_class="col-12 col-md-6"),
            ),
            Row(
                Column("motive", css_class="col-12"),
            ),
            Row(
                Column("observations", css_class="col-12"),
            ),
        )

        self.fields["order_type"].initial = InventoryOrder.OrderType.OUTBOUND.value
        self.fields["order_type"].widget = forms.HiddenInput()

        if not self.instance.pk:
            self.fields["status"].initial = InventoryOrder.StatusType.COMPLETED
            self.fields["status"].required = False


class OutboundOrderDetailBaseForm(forms.ModelForm):
    supply = forms.ModelChoiceField(
        queryset=Supply.objects.all(),
        to_field_name="code",
        widget=forms.Select(attrs={"class": "form-control"}),
        error_messages={"invalid_choice": "El insumo seleccionado no existe."},
    )

    class Meta:
        model = OrderDetail
        fields = [
            "supply",
            "quantity_requested",
            "observations",
        ]
        widgets = {
            # "supply": forms.Select(attrs={"class": "form-control"}),
            "quantity_requested": forms.NumberInput(attrs={"class": "form-control text-center"}),
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

        for field in self.fields.values():
            field.label = ""


OutboundOrderDetailFormSet = inlineformset_factory(
    InventoryOrder,
    OrderDetail,
    extra=1,
    form=OutboundOrderDetailBaseForm,
    can_delete=True,
    max_num=30,
)
