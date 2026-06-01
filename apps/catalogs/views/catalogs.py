import logging

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from pydantic import ValidationError

from apps.catalogs.forms import CatalogBaseForm, CatalogFilterForm
from apps.catalogs.layers.applications import CatalogAppService
from apps.catalogs.models import Catalog
from apps.core.views.base import (
    CustomCreateView,
    CustomDetailView,
    CustomListView,
    CustomUpdateView,
)
from apps.security.layers.security import SecurityService

logger = logging.getLogger(__name__)

DEFAULT_MODEL = Catalog
DEFAULT_LIST_URL = reverse_lazy("catalogs:catalogs:list")


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class CatalogListView(CustomListView):
    model = DEFAULT_MODEL
    form_class = CatalogFilterForm
    success_url: str = DEFAULT_LIST_URL
    template_name = "catalogs/datatable.html"
    permission_required = "catalogs.view_Catalog"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["object"] = self.model
        ctx["description"] = _("Management of registered catalogs")
        ctx["actions"]["menu_actions"]["add"]["url"] = reverse_lazy("catalogs:catalogs:create")

        return ctx

    def retrieve_data(self, params):
        return CatalogAppService().retrieve_catalogs(params)

    def get_success_url(self):
        return self.success_url


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class CatalogDetailView(CustomDetailView):
    app_name = "catalogs"
    model = DEFAULT_MODEL
    success_url: str = DEFAULT_LIST_URL
    template_name = "catalogs/detail.html"
    permission_required = ["catalogs.view_catalog", "catalogs.view_catalogitem"]

    def get_object(self, queryset=None):
        """Cache the object to avoid duplicate queries."""
        if not hasattr(self, "_cached_object"):
            self._cached_object = super().get_object(queryset)  # noqa
        return self._cached_object

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["is_admin"] = SecurityService.is_admin(self.request.user)

        catalog = self.get_object()
        ctx["total_items"] = catalog.items.count()
        ctx["active_items"] = catalog.items.filter(is_active=True).count()
        ctx["filter_form"] = CatalogFilterForm()
        ctx["items_url"] = reverse_lazy(
            "catalogs:items:list", kwargs={"catalog_reference": catalog.external_id}
        )
        #   {'title': 'Accionable', 'actions': [{'icon': 'bi bi-pencil-square', 'order': 0, 'title': 'Editar', 'action': 'update', 'description': '', 'url': '/catalogs/be7e4974-2d35-4333-a226-d6801cf0854a/update/'}]}

        actions = ctx["actions"]
        actions["actions"].insert(
            0,
            {
                "icon": "bi bi-plus-lg",
                "order": 1,
                "title": _("Add item"),
                "action": "add_item",
                "description": "",
                "url": reverse_lazy(
                    "catalogs:items:create", kwargs={"catalog_reference": catalog.external_id}
                ),
            },
        )
        ctx["actions"] = actions

        return ctx

    def get_success_url(self):
        return self.success_url


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class CatalogCreateView(CustomCreateView):
    model = DEFAULT_MODEL
    form_class = CatalogBaseForm
    success_url: str = DEFAULT_LIST_URL
    permission_required = "catalogs.add_catalog"
    template_name = "catalogs/create_or_update.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if "form" not in ctx:
            ctx["form"] = self.get_form()

        return ctx

    def post(self, request, *args, **kwargs):
        form = self.get_form()

        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def form_valid(self, form, **kwargs):
        service = CatalogAppService()

        try:
            data = form.cleaned_data
            service.register_catalog(payload={**data})
            messages.success(
                self.request,
                self.success_message.format(model=self.model._meta.verbose_name),
                extra_tags="toast",
            )
            return redirect(self.success_url)

        except ValidationError as e:
            self.handle_pydantic_error(e, form)
            return self.form_invalid(form)
        except Exception as e:
            return self.handle_error(str(e), e)

    def form_invalid(self, form):
        messages.warning(self.request, self.failure_message)
        return self.render_to_response(self.get_context_data(form=form))


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class CatalogUpdateView(CustomUpdateView):
    model = DEFAULT_MODEL
    form_class = CatalogBaseForm
    success_url: str = DEFAULT_LIST_URL
    permission_required = "catalogs.change_catalog"
    template_name = "catalogs/create_or_update.html"

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def get_object(self, queryset=None):
        if not hasattr(self, "_cached_object"):
            self._cached_object = super().get_object(queryset)  # noqa
        return self._cached_object

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if "form" not in ctx:
            ctx["form"] = self.get_form()

        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()

        if form.is_valid():
            return self.form_valid(form)

        return self.form_invalid(form)

    def form_valid(self, form):
        service = CatalogAppService()
        data = form.cleaned_data
        try:
            instance = service.update_catalog(
                instance=self.get_object(),
                payload={**data},
            )

            reference = instance.code[:10]
            model_name = self.model._meta.verbose_name
            messages.success(
                self.request,
                self.success_message.format(model=model_name, instance=reference),
                extra_tags="toast",
            )
            return redirect(self.get_success_url())

        except ValidationError as e:
            self.handle_pydantic_error(e, form)
            return self.form_invalid(form)
        except Exception as e:
            return self.handle_error(str(e), e)

    def form_invalid(self, form):
        messages.warning(self.request, self.failure_message)
        return self.render_to_response(self.get_context_data(form=form))
