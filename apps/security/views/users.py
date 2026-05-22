import logging
from uuid import uuid4

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView, ListView, UpdateView
from pydantic import ValidationError

from apps.core.layers.dto import DataTableParams
from apps.core.utils.constants import LabelEnum, MessageEnum
from apps.security.forms import PasswordUpdateForm, UserCreateForm, UserFilterForm, UserUpdateForm
from apps.security.layers.applications import UserAppService
from apps.security.models import Person, User

logger = logging.getLogger(__name__)

DEFAULT_MODEL = User
DEFAULT_SECOND_MODEL = Person
DEFAULT_LIST_URL = reverse_lazy("security:users:list")


class UserListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = DEFAULT_MODEL
    second_model = DEFAULT_SECOND_MODEL
    success_url = DEFAULT_LIST_URL
    template_name = "users/datatable.html"
    permission_required = ["security.view_user", "security.view_person"]

    def get_context_data(self, **kwargs):
        user = self.request.user
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "object": self.model,
                "person": self.second_model,
                "filter_form": UserFilterForm(),
                "list_url": self.success_url,
                "title": self.model._meta.verbose_name_plural,
                "ui_map": self.model.Status.get_ui_map(),
                "table_actions": self.get_table_actions(user),
                "status_choices": self.model.StatusChoices.choices,
            }
        )
        return context

    def get(self, request, *args, **kwargs):
        if self.is_ajax_request(request):
            return self.handle_datatable_request(request)
        return super().get(request, *args, **kwargs)

    @staticmethod
    def is_ajax_request(request):
        return request.headers.get("x-requested-with") == "XMLHttpRequest"

    def handle_datatable_request(self, request):
        params = DataTableParams(request, **request.GET)
        try:
            result = UserAppService().retrieve_users(params)
            return JsonResponse(result, safe=True)
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Error en Datatable: {e}", exc_info=True)
            return JsonResponse(params.result([]))


    def get_table_actions(self, user):
        all_actions = {
            "edit": {
                "label": LabelEnum.EDIT.value,
                "icon": "bi bi-pencil-square",
                "url": reverse_lazy("security:users:update", kwargs={"external_id": uuid4()}),
                "perm": user.has_perms(["security.change_user", "security.change_person"]),
            },
            "status": {
                "label": LabelEnum.STATUS.value,
                "icon": "",
                "perm": user.has_perms(["security.change_user", "security.change_person"]),
            },
            "view": {
                "label": LabelEnum.DETAILS.value,
                "icon": "bi bi-eye",
                "perm": user.has_perms(["security.view_user", "security.view_person"]),
            },
            "delete": {
                "label": LabelEnum.DELETE.value,
                "icon": "bi bi-trash",
                "perm": user.has_perms(["security.delete_user", "security.delete_person"]),
                "danger": 1,
            },
        }

        return {
            key: {k: v for k, v in action.items() if k != "perm"}
            for key, action in all_actions.items()
            if action.get("perm") is True
        }


class UserCreateView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    model = DEFAULT_MODEL
    form_class = UserCreateForm
    success_url = DEFAULT_LIST_URL
    failure_message = MessageEnum.FAILURE.value
    template_name = "users/create_or_update.html"
    permission_required = ["security.add_user", "security.add_person"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("Create User")
        context["cancel_url"] = self.success_url
        if "form" not in context:
            context["form"] = self.get_form()
        return context

    def post(self, request, *args, **kwargs):
        form = self.get_form()

        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def form_valid(self, form):
        service = UserAppService()
        try:
            payload = {
                **form.cleaned_data,
                "username": form.cleaned_data["document_number"],
                "password": form.cleaned_data["document_number"],
                "groups": ["specialist"],
            }

            self.object = service.register_user(payload=payload)
            messages.success(
                self.request,
                MessageEnum.CREATED.value.format(model=self.object.__class__.__name__.lower()),
            )
            return redirect(str(self.success_url))
        except ValidationError as e:
            for error in e.errors():
                field = error.get("loc", [None])[0]
                message = error.get("msg", "").replace("Value error, ", "")
                form.add_error(field if field in form.fields else None, message)
        except ValueError as e:
            form.add_error(None, str(e))
        except Exception as e:
            logger.error(f"Unexpected in {self.__class__.__name__}: {e}", exc_info=True)
            messages.error(self.request, MessageEnum.FAILURE_REQUEST.value)
        return self.form_invalid(form)

    def form_invalid(self, form):
        messages.warning(self.request, self.failure_message)
        return self.render_to_response(self.get_context_data(form=form))


class UserUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = DEFAULT_MODEL
    slug_field = "external_id"
    slug_url_kwarg = "external_id"
    form_class = UserUpdateForm
    success_url = DEFAULT_LIST_URL
    success_message = MessageEnum.SUCCESS.value
    failure_message = MessageEnum.FAILURE.value
    template_name = "users/create_or_update.html"
    permission_required = ["security.change_user", "security.change_person"]
    extra_context = {"title": _("Update User"), "cancel_url": DEFAULT_LIST_URL}

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.get_object().person
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["email"].initial = self.get_object().email
        return form

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = _("Update User")
        return ctx

    def form_valid(self, form):
        try:
            service = UserAppService()
            service.update_user(
                user=self.get_object(),
                payload=form.cleaned_data,
            )
            messages.success(self.request, self.success_message)
            return redirect(str(self.success_url))
        except ValidationError as e:
            for error in e.errors():
                loc = error.get("loc") or []
                field = loc[0] if loc else None
                message = error.get("msg", "").replace("Value error, ", "")
                form.add_error(field if field and field in form.fields else None, message)
            return self.form_invalid(form)
        except ValueError as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)
        except Exception as e:
            logger.error(f"Unexpected in {self.__class__.__name__}: {e}", exc_info=True)
            messages.error(self.request, MessageEnum.FAILURE_REQUEST.value)
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.warning(self.request, self.failure_message)
        return self.render_to_response(self.get_context_data(form=form))


class UserPasswordUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = DEFAULT_MODEL
    slug_field = "external_id"
    slug_url_kwarg = "external_id"
    form_class = PasswordUpdateForm
    success_message = MessageEnum.SUCCESS.value
    failure_message = MessageEnum.FAILURE.value
    success_url = reverse_lazy("security:login")
    permission_required = "security.change_user"
    template_name = "users/password/password_reset_confirm.html"
    extra_context = {
        "title": _("Update password"),
        "password_title": _(
            "To update your password, please keep the following security guidelines in mind:"
        ),
        "password_rules": [
            _("Must be at least <strong>8</strong> characters long."),
            _("Cannot be entirely numeric."),
            _("Cannot be a commonly used password."),
            _("Must include at least one special character (@, #, $, !)."),
            _("Cannot be too similar to your other personal information."),
        ],
    }

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj != self.request.user:
            raise PermissionDenied(_("You do not have permission to edit other users' accounts."))
        return obj

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.form_class(request.POST, instance=self.object)

        if form.is_valid():
            return self.form_valid(form)

        return self.form_invalid(form)

    def form_valid(self, form):
        try:
            service = UserAppService()
            service.update_password(
                request_user=self.request.user,
                payload={"user": self.get_object(), **form.cleaned_data},
            )

            messages.success(self.request, self.success_message)
            return redirect(str(self.success_url))
        except ValidationError as e:
            for error in e.errors():
                field = error.get("loc", [None])[0]
                message = error.get("msg", "").replace("Value error, ", "")
                form.add_error(field if field in form.fields else None, message)
        except ValueError as e:
            form.add_error(None, str(e))
        except PermissionDenied:
            messages.error(self.request, _("You do not have permission to perform this action."))
            return redirect("core:home")

        return self.form_invalid(form)

    def form_invalid(self, form):
        messages.warning(self.request, self.failure_message)
        return super().form_invalid(form)
