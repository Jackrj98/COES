from crispy_forms.helper import FormHelper
from django import forms
from django.contrib.auth import get_user_model

from apps.security.models import Person

User = get_user_model()


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["email"]
        widgets = {
            "email": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej:. jhon.doe@example.com"}
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_errors = True
        self.helper.error_text_inline = True
        self.helper.label_class = "form-label"
        self.helper.form_class = "needs-validation"


class PersonForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = ["first_name", "last_name", "document_number", "phone"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "jon"}),
            "last_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "doe"}),
            "document_number": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "12345"}
            ),
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
