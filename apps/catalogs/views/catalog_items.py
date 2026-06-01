import logging

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from pydantic import ValidationError

from apps.catalogs.forms import CatalogFilterForm, CatalogItemBaseForm
from apps.catalogs.layers.applications import CatalogItemAppService
from apps.catalogs.models import CatalogItem
from apps.core.views.base import (
    CustomCreateView,
    CustomDetailView,
    CustomListView,
    CustomUpdateView,
)
from apps.security.layers.security import SecurityService

logger = logging.getLogger(__name__)

DEFAULT_MODEL = CatalogItem
DEFAULT_LIST_URL = reverse_lazy("catalogs:items:list")


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class CatalogItemListView(CustomListView):
    model = DEFAULT_MODEL
    form_class = CatalogFilterForm
    slug_field = "catalog__external_id"
    slug_url_kwarg = "catalog_reference"
    success_url: str = DEFAULT_LIST_URL
    template_name = "catalogs/items/datatable.html"
    permission_required = "catalogs.view_catalogitem"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["description"] = _("Management of registered catalog items")
        return ctx

    def retrieve_data(self, params):
        catalog_reference = self.kwargs.get(self.slug_url_kwarg)

        return CatalogItemAppService().retrieve_items(params, catalog_reference)

    def get_success_url(self):
        catalog_reference = self.kwargs.get("catalog_reference")
        kwargs = {"catalog_reference": catalog_reference}
        return reverse_lazy("catalogs:items:detail", kwargs=kwargs)


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class CatalogItemDetailView(CustomDetailView):
    app_name = "items"
    model = DEFAULT_MODEL
    template_name = "catalogs/items/detail.html"
    permission_required = "catalogs.view_catalogitem"

    def get_object(self, queryset=None):
        """Cache the object to avoid duplicate queries."""
        if not hasattr(self, "_cached_object"):
            self._cached_object = super().get_object(queryset)  # noqa
        return self._cached_object

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        instance = self.get_object()
        ctx["is_admin"] = SecurityService.is_admin(self.request.user)

        catalog_kwargs = {"external_id": instance.catalog.external_id}

        breadcrumbs = ctx.get("breadcrumb", [])
        breadcrumbs[0] = {
            "name": instance.catalog.code,
            "url": reverse_lazy("catalogs:catalogs:detail", kwargs=catalog_kwargs),
        }
        breadcrumbs.insert(
            0, {"name": _("Catalogs"), "url": reverse_lazy("catalogs:catalogs:list")}
        )
        ctx["breadcrumbs"] = breadcrumbs
        actions = ctx["actions"]
        actions["actions"][0]["url"] = reverse_lazy(
            "catalogs:items:update",
            kwargs={
                "catalog_reference": instance.catalog.external_id,
                "external_id": instance.external_id,
            },
        )
        ctx["actions"] = actions
        return ctx

    def get_success_url(self):
        catalog_reference = self.kwargs.get("catalog_reference")
        kwargs = {"catalog_reference": catalog_reference, "external_id": self.object.external_id}
        return reverse_lazy("catalogs:items:detail", kwargs=kwargs)


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class CatalogItemCreateView(CustomCreateView):
    model = DEFAULT_MODEL
    form_class = CatalogItemBaseForm
    permission_required = "catalogs.add_catalog"
    template_name = "catalogs/items/create_or_update.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["catalog_reference"] = self.kwargs.get("catalog_reference")
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if "form" not in ctx:
            ctx["form"] = self.get_form()

        kwargs = {"external_id": self.kwargs.get("catalog_reference")}
        breadcrumbs = ctx.get("breadcrumb", [])
        breadcrumbs.insert(
            0, {"name": _("Catalogs"), "url": reverse_lazy("catalogs:catalogs:list")}
        )
        ctx["breadcrumbs"] = breadcrumbs

        url = reverse_lazy("catalogs:catalogs:detail", kwargs=kwargs)
        ctx["list_url"] = url
        ctx["cancel_url"] = url
        return ctx

    def post(self, request, *args, **kwargs):
        form = self.get_form()

        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def form_valid(self, form, **kwargs):
        data = form.cleaned_data
        service = CatalogItemAppService()

        try:
            service.register_item(
                payload={**data}, catalog_reference=self.kwargs.get("catalog_reference")
            )
            messages.success(
                self.request,
                self.success_message.format(model=self.model._meta.verbose_name),
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

    def get_success_url(self):
        catalog_reference = self.kwargs.get("catalog_reference")
        kwargs = {"external_id": catalog_reference}
        return reverse_lazy("catalogs:catalogs:detail", kwargs=kwargs)


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class CatalogItemUpdateView(CustomUpdateView):
    model = DEFAULT_MODEL
    form_class = CatalogItemBaseForm
    permission_required = "catalogs.change_catalog"
    template_name = "catalogs/items/create_or_update.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["catalog_reference"] = self.kwargs.get("catalog_reference")
        return kwargs

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def get_object(self, queryset=None):
        if not hasattr(self, "_cached_object"):
            self._cached_object = super().get_object(queryset)  # noqa
        return self._cached_object

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        instance = self.get_object()
        if "form" not in ctx:
            ctx["form"] = self.get_form()

        instance = self.get_object()
        catalog_kwargs = {"external_id": instance.catalog.external_id}

        breadcrumbs = ctx.get("breadcrumb", [])
        breadcrumbs[0] = {
            "name": instance.catalog.code,
            "url": reverse_lazy("catalogs:catalogs:detail", kwargs=catalog_kwargs),
        }
        breadcrumbs.insert(
            0, {"name": _("Catalogs"), "url": reverse_lazy("catalogs:catalogs:list")}
        )
        ctx["breadcrumbs"] = breadcrumbs
        ctx["list_url"] = instance.get_absolute_url()
        ctx["cancel_url"] = instance.get_absolute_url()
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()

        if form.is_valid():
            return self.form_valid(form)

        return self.form_invalid(form)

    def form_valid(self, form):
        service = CatalogItemAppService()
        data = form.cleaned_data
        try:
            instance = service.update_item(
                instance=self.get_object(),
                payload={**data},
                catalog_reference=self.kwargs.get("catalog_reference"),
            )

            reference = instance.code[:10]
            model_name = self.model._meta.verbose_name
            messages.success(
                self.request,
                self.success_message.format(model=model_name, instance=reference),
                extra_tags="toast",
            )
            return redirect(instance.get_absolute_url())

        except ValidationError as e:
            self.handle_pydantic_error(e, form)
            return self.form_invalid(form)
        except Exception as e:
            return self.handle_error(str(e), e)

    def form_invalid(self, form):
        messages.warning(self.request, self.failure_message)
        return self.render_to_response(self.get_context_data(form=form))

    def get_success_url(self):
        return redirect(self.object.get_absolute_url())
