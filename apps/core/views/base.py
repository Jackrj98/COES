import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import redirect
from django.urls import NoReverseMatch, reverse
from django.utils.text import capfirst
from django.utils.translation import gettext_lazy as _
from django.views.generic import DeleteView, DetailView, FormView, ListView, UpdateView
from django.views.generic.base import ContextMixin

from apps.core.forms.base import BaseFilterForm
from apps.core.mixins import DatatableMixin
from apps.core.mixins.breadcrumb import BreadcrumbMixin
from apps.core.utils.constants import LabelEnum, MessageEnum

logger = logging.getLogger(__name__)


class BaseView(LoginRequiredMixin, PermissionRequiredMixin, ContextMixin, BreadcrumbMixin):
    model = None
    success_url = None
    template_name = None
    success_message: str = MessageEnum.SUCCESS.value
    failure_message: str = MessageEnum.FAILURE.value

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = self.get_title()
        ctx["list_url"] = self.success_url
        ctx["cancel_url"] = self.success_url
        ctx["breadcrumb"] = self.build_breadcrumb()

        if self.model:
            ctx["parent"] = _(self.model._meta.verbose_name_plural).title()  # noqa

        return ctx

    def get_title(self):
        if self.extra_context and self.extra_context.get("title"):
            return self.extra_context["title"]

        if self.model:
            if hasattr(self, "object_list"):
                return _(self.model._meta.verbose_name_plural).capitalize()  # noqa

        return self.model._meta.verbose_name.capitalize()  # noqa

    def handle_error(self, msg: str, error: Exception):
        """Centralized error handling with secure redirection."""
        logger.exception(f"[{self.__class__.__name__}]: {msg} — {error}")
        messages.error(self.request, self.failure_message)  # noqa
        return redirect(self.success_url or "/")


class CustomListView(BaseView, DatatableMixin, ListView):
    form_class = BaseFilterForm

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["current_page"] = True
        ctx["actions"] = self.get_actions()
        ctx["filter_form"] = self.form_class()
        if self.model.IsActiveChoices:
            ctx["status_choices"] = self.model.IsActiveChoices.choices

        if self.model.IsActiveColorChoices:
            ctx["status_color_choices"] = self.model.IsActiveColorChoices.choices

        return ctx

    def get_actions(self):
        return {
            "menu_actions": {
                "title": LabelEnum.ACTIONS.value,
                "add": {
                    "title": LabelEnum.ADD.value.format(model=self.model._meta.verbose_name)  # noqa
                },
            }
        }


class CustomDetailView(BaseView, DetailView):
    app_name = None
    slug_field = "external_id"
    slug_url_kwarg = "external_id"

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = self.model.IsActiveChoices.choices
        ctx["status_color_choices"] = self.model.IsActiveColorChoices.choices

        # Build actions
        actions_list = self._build_base_actions()
        ctx["actions"] = {
            "title": LabelEnum.ACTIONS.value,
            "actions": sorted(actions_list, key=lambda x: x["order"]),
        }
        return ctx

    def _build_base_actions(self):
        """Build the base list of actions with permission checking."""
        app_label = self.model._meta.app_label  # noqa
        model_name = self.model._meta.model_name  # noqa
        actions_list = []

        # Edit action
        edit_action = self.get_actions_map(
            title=LabelEnum.ACTIONS.EDIT.value.format(model=model_name),
            order=1,
            action="update",
            icon="bi bi-pencil-square",
            url_name=f"{app_label}:{self.app_name}:update",
            perm=f"{app_label}.change_{model_name}",
        )

        if edit_action:
            actions_list.append(edit_action)

        return actions_list

    def get_actions_map(self, title, order, action, icon, url_name, **kwargs):
        """Create an action dictionary if the user has permission."""
        # Check if object exists before accessing it
        if not hasattr(self, "object") or self.object is None:
            return None

        permission = kwargs.get("perm", "")
        description = kwargs.get("description", "")

        # Skip permission check if no permission required
        if permission and not self.request.user.has_perm(permission):
            return None

        url_kwargs = {self.slug_url_kwarg: getattr(self.object, self.slug_field)}

        return {
            "icon": icon,
            "order": order,
            "title": title,
            "action": action,
            "description": description,
            "url": self.safe_reverse(url_name, url_kwargs),
        }

    def add_custom_action(self, context, action, permission=None):

        # Check permission if required
        if permission and not self.request.user.has_perm(permission):
            return

        custom_action = action
        actions = context.get("actions", {})
        actions_list = actions.get("actions", [])

        # Insert maintaining order (avoid duplicates by title or action)
        existing = any(
            a.get("action") == custom_action["name"] or a.get("title") == custom_action["title"]
            for a in actions_list
        )

        if not existing:
            actions_list.append(custom_action)
            # Re-sort after adding
            actions_list.sort(key=lambda x: x["order"])
            actions["actions"] = actions_list
            context["actions"] = actions

    @staticmethod
    def safe_reverse(name, kwargs=None):
        try:
            return reverse(name, kwargs=kwargs)
        except NoReverseMatch:
            logger.warning(f"URL reverse not found: {name}")
            return "#"


class BaseActionView(BaseView):
    """Intermediate class for sharing form logic."""

    def form_valid(self, form):
        response = super().form_valid(form)  # noqa
        if hasattr(self, "success_message"):
            messages.success(self.request, self.success_message)  # noqa
        return response

    def form_invalid(self, form):
        messages.warning(
            self.request,  # noqa
            getattr(self, "failure_message"),
        )
        return super().form_invalid(form)  # noqa

    def get_action_title(self, action_label):
        """Centralize the generation of the title."""
        model_name = capfirst(self.model._meta.verbose_name)  # noqa
        return action_label.format(model=model_name)

    @staticmethod
    def handle_pydantic_error(e, form, second_form=None):
        for error in e.errors():
            loc = error.get("loc") or []
            field = loc[0] if loc else None
            message = error.get("msg", "").replace("Value error, ", "")

            if field:
                if field in form.fields:
                    form.add_error(field, message)
                elif second_form and field in second_form.fields:
                    second_form.add_error(field, message)
                else:
                    form.add_error(None, message)
            else:
                form.add_error(None, message)


class CustomCreateView(BaseActionView, FormView):
    success_message = MessageEnum.CREATED.value

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = self.get_action_title(LabelEnum.ADD_MODEL.value)
        if "form" not in ctx:
            ctx["form"] = self.get_form()
        return ctx

    def build_breadcrumb(self, extra_breadcrumb=None):
        verbose_name = _(self.model._meta.verbose_name)  # noqa
        return super().build_breadcrumb(
            extra_breadcrumb={
                "name": LabelEnum.ADD_MODEL.format(model=verbose_name),
                "url": "#",
                "active": True,
                "title": LabelEnum.ADD.value,
            }
        )


class CustomUpdateView(BaseActionView, UpdateView):
    slug_field = "external_id"
    slug_url_kwarg = "external_id"
    success_message = MessageEnum.UPDATED.value

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_url"] = self.get_success_url()
        ctx["title"] = self.get_action_title(LabelEnum.EDIT_MODEL.value)
        ctx["detail_url"] = (getattr(self.object, "get_absolute_url", lambda: "#")(),)

        return ctx

    def build_breadcrumb(self, extra_breadcrumb=None):
        verbose_name = _(self.model._meta.verbose_name)  # noqa
        return super().build_breadcrumb(
            extra_breadcrumb={
                "name": LabelEnum.EDIT_MODEL.format(model=verbose_name),
                "url": "#",
                "active": True,
                "title": LabelEnum.EDIT.value,
            }
        )

    def get_success_url(self):
        referer = self.request.META.get("HTTP_REFERER", "")
        if str(self.object.external_id) in referer:
            return self.object.get_absolute_url()

        return self.success_url


class CustomStatusUpdateView(BaseActionView, UpdateView):
    slug_field = "external_id"
    slug_url_kwarg = "external_id"
    success_message = MessageEnum.SUCCESS.value


class BaseDeleteView(BaseView, DeleteView):
    slug_field = "external_id"
    slug_url_kwarg = "external_id"
    success_message = MessageEnum.DELETED.value

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        model_name = self.model._meta.verbose_name  # noqa
        deletable, counts, protected = self.object.get_deleted_objects()

        ctx["protected"] = protected
        ctx["deletable_objects"] = deletable
        ctx["model_count"] = dict(counts).items()
        ctx["title"] = LabelEnum.DELETE_MODEL.value.format(model=model_name)
        ctx["cancel_url"] = getattr(self.object, "get_absolute_url", lambda: self.success_url)()
        return ctx

    def build_breadcrumb(self, extra_breadcrumb=None):
        verbose_name = _(self.model._meta.verbose_name)  # noqa

        return super().build_breadcrumb(
            extra_breadcrumb={
                "name": LabelEnum.DELETE_MODEL.format(model=verbose_name),
                "url": "#",
                "active": True,
                "title": LabelEnum.DELETE.value,
            }
        )

    def form_valid(self, form):
        self.object = self.get_object()
        success_url = self.get_success_url()

        try:
            if hasattr(self.object, "soft_delete"):
                self.object.soft_delete()
            else:
                self.object.delete()
            messages.success(self.request, self.success_message, extra_tags="toast")
        except Exception as e:
            logger.exception(f"Error in soft delete for {self.model.__name__}: {e}")
            return self.handle_error(f"Unexpected error deleting {self.model.__name__}", e)

        return redirect(success_url)
