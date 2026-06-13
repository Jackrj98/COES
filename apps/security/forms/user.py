from crispy_forms.helper import FormHelper
from django import forms
from django.utils.functional import lazy
from django.utils.translation import gettext_lazy as _

from apps.core.forms import BaseFilterForm, BaseFormHelperMixin
from apps.security.layers.applications import UserAppService
from apps.security.models import Person, User


class UserFilterForm(BaseFilterForm, BaseFormHelperMixin):
    status = forms.ChoiceField(
        label=_("Status"),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    group = forms.ChoiceField(
        label=_("Group"),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        search_text = _("Search")
        if "search" in self.fields:
            self.fields["search"].label = search_text
            self.fields["search"].widget.attrs.update(
                {"placeholder": _("Search by names, username, email"), "class": "form-control"}
            )

        self.setup_form_helper(
            label_class="form-label text-sm text-muted", form_class="needs-validation"
        )
        status_choices = BaseFilterForm.DEFAULT_CHOICE + list(User.Status.choices)  # type: ignore
        groups_choices = (
            BaseFilterForm.DEFAULT_CHOICE + lazy(UserAppService.retrieve_groups, list)()
        )
        self.fields["status"].choices = status_choices
        self.fields["group"].choices = groups_choices


class PersonBaseForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = ["first_name", "last_name", "document_number", "phone"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Jon"}),
            "last_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Doe"}),
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


class UserCreateForm(forms.ModelForm):
    group = forms.ChoiceField(
        label=_("Group"),
        required=True,
        choices=BaseFilterForm.DEFAULT_CHOICE + list(UserAppService().retrieve_groups()),
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = User
        fields = ["email"]
        widgets = {
            "email": forms.TextInput(attrs={"placeholder": "Ej: jhon.doe@example.com"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_errors = True
        self.helper.error_text_inline = True
        self.helper.label_class = "form-label"
        self.helper.form_class = "needs-validation"


class UserUpdateForm(forms.ModelForm):
    group = forms.ChoiceField(
        label=_("Group"),
        required=False,
        disabled=True,
        choices=BaseFilterForm.DEFAULT_CHOICE + list(UserAppService().retrieve_groups()),
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = User
        fields = ["email"]
        widgets = {
            "email": forms.TextInput(attrs={"placeholder": "Ej: jhon.doe@example.com"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_errors = True
        self.helper.error_text_inline = True
        self.helper.label_class = "form-label"
        self.helper.form_class = "needs-validation"

        self.fields["email"].required = False
        self.fields["email"].disabled = True


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

    def clean(self):
        user = self.instance
        current = self.cleaned_data.get("current_password")
        new_password = self.cleaned_data.get("new_password")
        confirm_password = self.cleaned_data.get("confirm_password")

        if user and not user.check_password(current):
            self.add_error("current_password", _("Current password is incorrect"))

        if new_password == current:
            self.add_error(
                "new_password", _("New password cannot be the same as the current password")
            )

        if new_password != confirm_password:
            self.add_error("new_password", _("Passwords do not match"))
            self.add_error("confirm_password", _("Passwords do not match"))

        return self.cleaned_data
