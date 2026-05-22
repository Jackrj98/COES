from crispy_forms.helper import FormHelper
from django import forms
from django.utils.translation import gettext_lazy as _

from apps.core.forms import BaseFilterForm, BaseFormHelperMixin
from apps.security.models import Person, User


class UserCreateForm(forms.ModelForm):
    email = forms.EmailField(
        required=True,
        label=_("Email"),
        widget=forms.TextInput(attrs={"placeholder": "Ej:. jhon.doe@example.com"}),
    )

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


class UserFilterForm(BaseFilterForm, BaseFormHelperMixin):
    status = forms.ChoiceField(
        label=_("Status"),
        required=False,
        choices=BaseFilterForm.DEFAULT_CHOICE + list(User.Status.choices),
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        search_text = _("Search")
        if "search" in self.fields:
            self.fields["search"].label = search_text
            self.fields["search"].widget.attrs.update(
                {"placeholder": search_text, "class": "form-control"}
            )

        self.setup_form_helper(
            label_class="form-label text-sm text-muted", form_class="needs-validation"
        )


class PasswordUpdateForm(forms.ModelForm):
    current_password = forms.CharField(
        required=True,
        label=_("Current Password"),
        min_length=5,
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    new_password = forms.CharField(
        required=True,
        label=_("New Password"),
        widget=forms.PasswordInput(attrs={"class": "form-control", "minlength": 8}),
        validators=[],
    )
    confirm_password = forms.CharField(
        required=True,
        label=_("Confirm New Password"),
        min_length=8,
        widget=forms.PasswordInput(attrs={"class": "form-control", "equal_to": "new_password"}),
        validators=[],
    )

    class Meta:
        model = User
        fields = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_errors = True
        self.helper.error_text_inline = True
        self.helper.label_class = "form-label"
        self.helper.form_class = "needs-validation"
        self.fields["current_password"].widget.attrs["autofocus"] = True
