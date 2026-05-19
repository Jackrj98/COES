from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView

from apps.core.utils.constants import MessageEnum
from apps.security.forms.user import PersonForm, UserForm
from apps.security.layers.applications.user_service import UserAppService
from apps.security.models import Person, User

DEFAULT_MODEL = User
DEFAULT_SECOND_MODEL = Person


class UserCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = DEFAULT_MODEL
    second_model = DEFAULT_MODEL
    form_class = UserForm
    second_form_class = PersonForm
    template_name = "users/create_or_update.html"
    permission_required = ["security.add_user"]
    success_url = reverse_lazy("core:home")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("Create User")
        context["user_form"] = self.form_class
        context["person_form"] = self.second_form_class
        return context

    def post(self, request, *args, **kwargs):
        self.object = None
        user_form = self.form_class(request.POST)
        person_form = self.second_form_class(request.POST)

        if all([user_form.is_valid(), person_form.is_valid()]):
            return self.form_valid(user_form, person_form=person_form)

        return self.form_invalid(user_form, person_form=person_form)

    def form_valid(self, form, **kwargs):
        service = UserAppService()
        person_form = kwargs.pop("person_form")

        user_payload = form.cleaned_data
        payload = person_form.cleaned_data
        payload["email"] = user_payload["email"]

        instance = service.create_user(payload)

        messages.success(
            self.request, MessageEnum.CREATED.value.format(model=instance.__class__.__name__)
        )
        return redirect(self.success_url)

    def form_invalid(self, form, **kwargs):

        messages.warning(self.request, "Please correct the errors")
        context = self.get_context_data()
        context["user_form"] = form
        context["person_form"] = kwargs.get("person_form")
        return self.render_to_response(context)
