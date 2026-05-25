import logging
from uuid import uuid4

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from pydantic import ValidationError

from apps.core.utils.constants import LabelEnum, MessageEnum
from apps.core.views.base import (
    CustomCreateView,
    CustomDetailView,
    CustomListView,
    CustomUpdateView,
)
from apps.security.forms import (
    PasswordUpdateForm,
    PersonBaseForm,
    UserCreateForm,
    UserFilterForm,
    UserUpdateForm,
)
from apps.security.layers.applications import EmailAppService, UserAppService
from apps.security.layers.security import SecurityService
from apps.security.models import Person, User

logger = logging.getLogger(__name__)

DEFAULT_MODEL = User
SECOND_MODEL = Person
DEFAULT_LIST_URL = reverse_lazy("security:users:list")


@method_decorator(user_passes_test(SecurityService.is_admin), name="dispatch")
class UserListView(CustomListView):
    model = DEFAULT_MODEL
    second_model = SECOND_MODEL
    form_class = UserFilterForm
    success_url: str = DEFAULT_LIST_URL
    template_name = "users/datatable.html"
    permission_required = ["security.view_user", "security.view_person"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        ctx["object"] = self.model
        ctx["person"] = self.second_model
        ctx["ui_map"] = self.model.Status.get_ui_map()
        ctx["table_actions"] = self.get_table_actions(user)
        ctx["status_choices"] = self.model.StatusChoices.choices
        return ctx

    def retrieve_data(self, params):
        return UserAppService().retrieve_users(params)

    def get_success_url(self):
        return self.success_url

    @staticmethod
    def get_table_actions(user):
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
                "url": reverse_lazy("security:users:status", kwargs={"external_id": uuid4()}),
                "perm": user.has_perms(["security.change_user", "security.change_person"]),
            },
            "view": {
                "label": LabelEnum.DETAILS.value,
                "icon": "bi bi-eye",
                "url": reverse_lazy("security:users:detail", kwargs={"external_id": uuid4()}),
                "perm": user.has_perms(["security.view_user", "security.view_person"]),
            },
        }

        return {
            key: {k: v for k, v in action.items() if k != "perm"}
            for key, action in all_actions.items()
            if action.get("perm") is True
        }


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class UserDetailView(CustomDetailView):
    app_name = "users"
    model = DEFAULT_MODEL
    success_url: str = DEFAULT_LIST_URL
    template_name = "users/detail.html"
    permission_required = ["security.view_user", "security.view_person"]

    def get_queryset(self):
        """Optimize a query with select_related."""
        return (
            self.model.objects.select_related("person")  # Solo una vez
            .prefetch_related("groups")
            .filter(deleted_at__isnull=True)
        )

    def get_object(self, queryset=None):
        """Cache the object to avoid duplicate queries."""
        if not hasattr(self, "_cached_object"):
            self._cached_object = super().get_object(queryset)
        return self._cached_object

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        current_user = request.user
        target_user = self.object
        is_admin = SecurityService.is_admin(current_user)

        # Non-admin users cannot view other users
        if target_user != current_user and not is_admin:
            messages.warning(request, _("You do not have permission to view this user's details."))
            return redirect(self.success_url)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = _("User Details")
        ctx["person"] = self.object.person
        ctx["ui_map"] = self.model.Status.get_ui_map()

        actions_list = ctx["actions"]["actions"]

        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name
        update_perm = f"{app_label}.change_{model_name}"

        current_user = self.request.user
        target_user = self.object
        is_admin = SecurityService.is_admin(current_user)

        is_viewing_self = target_user == current_user

        if is_viewing_self and not is_admin:
            # Remove the first breadcrumb item (the "List" action)
            if ctx.get("breadcrumb") and len(ctx["breadcrumb"]) > 0:
                ctx["breadcrumb"][-2]["title"] = _("Profile")
                ctx["breadcrumb"][-2]["name"] = _("Profile")
                ctx["breadcrumb"][-2]["url"] = "#"
                ctx["breadcrumb"][-2]["active"] = True

        # Determine password action type
        if is_admin:
            title = _("Reset Password")
            action = "reset_password"
            url_name = f"{app_label}:{self.app_name}:password_reset"
            target = target_user
        else:
            title = _("Update Password")
            action = "update_password"
            url_name = f"{app_label}:{self.app_name}:password_change"
            target = current_user  # Non-admin can only change their own password

        pwd_action = self.get_actions_map(
            title=title,
            order=1,
            action=action,
            icon="bi bi-key",
            url_name=url_name,
            perm=update_perm,
        )

        if pwd_action:
            pwd_action["url"] = reverse_lazy(url_name, kwargs={"external_id": target.external_id})
            actions_list.append(pwd_action)

            # Update edit action for non-admin viewing self
            if not is_admin and target_user == current_user:
                for action_item in actions_list:
                    if action_item.get("action") == "edit":
                        action_item["url"] = reverse_lazy(
                            "security:users:update",
                            kwargs={"external_id": current_user.external_id},
                        )
                        break

            actions_list.sort(key=lambda x: x["order"])

        return ctx

    def get_success_url(self):
        return self.success_url


@method_decorator(user_passes_test(SecurityService.is_admin), name="dispatch")
class UserCreateView(CustomCreateView):
    model = DEFAULT_MODEL
    form_class = UserCreateForm
    second_form_class = PersonBaseForm
    success_url: str = DEFAULT_LIST_URL
    template_name = "users/create_or_update.html"
    permission_required = ["security.add_user", "security.add_person"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if "form" not in ctx:
            ctx["form"] = self.get_form()

        if "person_form" not in ctx:
            ctx["person_form"] = self.second_form_class()

        return ctx

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        person_form = self.second_form_class(self.request.POST)

        if all([form.is_valid(), person_form.is_valid()]):
            return self.form_valid(form, person_form=person_form)
        return self.form_invalid(form, person_form=person_form)

    def form_valid(self, form, **kwargs):
        service = UserAppService()
        person_form = kwargs.get("person_form")

        try:
            user_data = form.cleaned_data
            person_data = person_form.cleaned_data
            user_data["groups"] = [user_data.pop("group")]
            user_data["username"] = person_data["document_number"]
            user_data["password"] = person_data["document_number"]

            service.register_user(payload={**person_data, **user_data})
            messages.success(
                self.request,
                self.success_message.format(model=self.model._meta.verbose_name),
                extra_tags="toast",
            )
            return redirect(self.success_url)

        except ValidationError as e:
            self.handle_pydantic_error(e, form, person_form)
            return self.form_invalid(form, person_form=person_form)
        except Exception as e:
            return self.handle_error(str(e), e)

    def form_invalid(self, form, **kwargs):
        person_form = kwargs.get("person_form")
        messages.warning(self.request, self.failure_message.value)
        return self.render_to_response(self.get_context_data(form=form, person_form=person_form))


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class UserUpdateView(CustomUpdateView):
    model = DEFAULT_MODEL
    form_class = UserUpdateForm
    second_form_class = PersonBaseForm
    success_url: str = DEFAULT_LIST_URL
    template_name = "users/create_or_update.html"
    permission_required = ["security.change_user", "security.change_person"]

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self.can_edit_user(request.user, self.object):
            messages.error(request, _("You do not have permission to edit this user."))
            return redirect(self.success_url)

        return super().dispatch(request, *args, **kwargs)

    @staticmethod
    def can_edit_user(current_user, target_user):
        if current_user.is_superuser:
            return True

        if current_user.groups.filter(name="administrator").exists():
            return True

        return current_user == target_user

    def get_queryset(self):
        return self.model.objects.select_related("person")

    def get_object(self, queryset=None):
        if not hasattr(self, "_cached_object"):
            self._cached_object = super().get_object(queryset)
        return self._cached_object

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["group"].initial = self.get_object().groups.first().name
        return form

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = _("Update User")
        referer = self.request.META.get("HTTP_REFERER", "")

        if str(self.object.external_id) in referer:
            ctx["cancel_url"] = self.object.get_absolute_url()
        else:
            ctx["cancel_url"] = self.success_url

        if "form" not in ctx:
            ctx["form"] = self.get_form()

        if "person_form" not in ctx:
            ctx["person_form"] = self.second_form_class(instance=self.get_object().person)
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        person_form = self.second_form_class(self.request.POST, instance=self.get_object().person)

        if all([form.is_valid(), person_form.is_valid()]):
            return self.form_valid(form, person_form=person_form)
        return self.form_invalid(form, person_form=person_form)

    def form_valid(self, form, **kwargs):
        service = UserAppService()
        person_form = kwargs.get("person_form")

        try:
            person_data = person_form.cleaned_data
            service.update_user(
                user=self.get_object(),
                payload={**person_data},
            )

            messages.success(
                self.request,
                self.success_message.format(
                    model=self.model._meta.verbose_name, instance=self.object.username
                ),
                extra_tags="toast",
            )
            return redirect(self.success_url)

        except ValidationError as e:
            self.handle_pydantic_error(e, form, person_form)
            return self.form_invalid(form, person_form=person_form)
        except Exception as e:
            return self.handle_error(str(e), e)

    def form_invalid(self, form, **kwargs):
        person_form = kwargs.get("person_form")
        messages.warning(self.request, self.failure_message.value)
        return self.render_to_response(self.get_context_data(form=form, person_form=person_form))


@method_decorator(user_passes_test(SecurityService.is_admin), name="dispatch")
class UserStatusUpdateView(CustomUpdateView):
    model = DEFAULT_MODEL
    slug_field = "external_id"
    slug_url_kwarg = "external_id"
    success_url: str = DEFAULT_LIST_URL
    permission_required = ["security.change_user"]

    @staticmethod
    def can_edit_user(current_user, target_user):
        if current_user.is_superuser:
            return True

        if current_user.groups.filter(name="administrator").exists():
            return True

        return current_user == target_user

    def get(self, request, *args, **kwargs):
        user = self.get_object()

        if not self.can_edit_user(request.user, user):
            messages.error(request, _("You do not have permission to edit this user."))
            return redirect(self.success_url)

        return JsonResponse(
            {
                "success": True,
                "title": _("Change Status"),
                "description": _("Are you sure you want to change the status of this user?"),
                "name": user.person.full_name,
                "email": user.email,
                "status": user.get_status_display(),
                "is_active": user.is_active,
            }
        )

    def post(self, request, *args, **kwargs):
        try:
            user = self.get_object()
            UserAppService().update_status(user)
            return JsonResponse({"success": True, "message": str(_(MessageEnum.SUCCESS.value))})
        except Exception as e:
            logger.error(f"Error updating status: {e}", exc_info=True)
            return JsonResponse(
                {"success": False, "message": str(_(MessageEnum.FAILURE.value))}, status=500
            )


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class UserPasswordUpdateView(CustomUpdateView):
    model = DEFAULT_MODEL
    form_class = PasswordUpdateForm
    success_url = reverse_lazy("security:login")
    permission_required = "security.change_user"
    template_name = "users/password/password_reset_confirm.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = _("Update password")
        ctx["cancel_url"] = self.object.get_absolute_url()
        ctx["password_title"] = _(
            "To update your password, please keep the following security guidelines in mind:"
        )
        ctx["password_rules"] = [
            _("Must be at least <strong>8</strong> characters long."),
            _("Cannot be entirely numeric."),
            _("Cannot be a commonly used password."),
            _("Must include at least one special character (@, #, $, !)."),
            _("Cannot be too similar to your other personal information."),
        ]
        return ctx

    def build_breadcrumb(self, extra_breadcrumb=None):
        parent_breadcrumb = super().build_breadcrumb()
        parent_breadcrumb.pop(-1)
        parent_breadcrumb.append(
            {
                "name": _("Update password"),
                "active": True,
                "title": _("Update password"),
            }
        )
        return parent_breadcrumb

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

            messages.success(
                self.request,
                self.success_message.format(
                    model=self.model._meta.verbose_name,
                    instance=self.object.username,
                ),
                extra_tags="toast",
            )
            return redirect(self.success_url)

        except ValidationError as e:
            self.handle_pydantic_error(e, form)
            return self.form_invalid(form)
        except PermissionDenied:
            messages.error(self.request, _("You do not have permission to perform this action."))
            return redirect("core:home")
        except Exception as e:
            self.handle_error(str(e), e)

    def form_invalid(self, form):
        messages.warning(self.request, self.failure_message.value)
        return self.render_to_response(self.get_context_data(form=form))


@user_passes_test(SecurityService.is_admin)
def send_reset_password(request, external_id):
    service = UserAppService()
    user: User = service.retrieve_by_external(external_id)

    new_password = service.generate_password()
    service.reset_password(request_user=user, password=new_password)

    subject = _("Password Reset Request")
    now_local = timezone.localtime(timezone.now())
    domain = settings.DOMAIN
    context = {
        "title": subject,
        "username": user.username,
        "password": new_password,
        "user": user.person.full_name,
        "url": f"{domain}{reverse_lazy('security:login')}",
        "formatted_date": now_local.strftime("%d/%m/%Y"),
        "formatted_time": now_local.strftime("%H:%M"),
    }

    EmailAppService.send(
        subj=str(subject),
        recp=[user.email],
        template="users/emails/reset_confirm_password.html",
        ctx=context,
    )

    messages.success(request, _("Reset email sent successfully."), extra_tags="toast")
    return redirect(user.get_absolute_url())
