import logging

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from pydantic import ValidationError

from apps.core.views.base import (
    CustomCreateView,
    CustomDetailView,
    CustomListView,
    CustomUpdateView,
)
from apps.inventory.forms import BatchBaseForm, BatchFilterForm
from apps.inventory.layers.applications import BatchAppService
from apps.inventory.models import Batch, Supply
from apps.security.layers.security import SecurityService

logger = logging.getLogger(__name__)

DEFAULT_MODEL = Batch
DEFAULT_LIST_URL = reverse_lazy("inventory:batches:list")


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class BatchListView(CustomListView):
    model = DEFAULT_MODEL
    form_class = BatchFilterForm
    slug_field = "supply__external_id"
    slug_url_kwarg = "supply_reference"
    success_url: str = DEFAULT_LIST_URL
    template_name = "supplies/datatable.html"
    permission_required = "inventory.view_batch"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        return ctx

    def retrieve_data(self, params):
        supply_reference = self.kwargs.get(self.slug_url_kwarg)
        return BatchAppService().retrieve_batches(params, supply_reference)

    def get_success_url(self):
        return self.success_url


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class BatchDetailView(CustomDetailView):
    """View for displaying supply details with stock information."""

    app_name = "supplies"
    model = DEFAULT_MODEL
    permission_required = "inventory.view_batch"
    template_name = "supplies/batches/detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = _("Batch Details")

        supply = Supply.objects.filter(external_id=self.kwargs.get("supply_reference")).first()
        if supply:
            breadcrumbs = ctx.get("breadcrumb", [])
            supplies_crumb = {"name": _("Supplies"), "url": reverse_lazy("inventory:supplies:list")}
            if supplies_crumb not in breadcrumbs:
                breadcrumbs.insert(0, supplies_crumb)

            if len(breadcrumbs) > 1:
                breadcrumbs[1].update(
                    {
                        "name": f"{supply.name} - {supply.code}",
                        "url": reverse_lazy(
                            "inventory:supplies:detail", kwargs={"external_id": supply.external_id}
                        ),
                    }
                )

            if breadcrumbs:
                breadcrumbs[-1].update({"name": _("Details"), "active": True, "url": None})

            ctx["breadcrumbs"] = breadcrumbs

        url_kwargs = {
            "supply_reference": self.kwargs.get("supply_reference"),
            "external_id": self.kwargs.get(self.slug_url_kwarg),
        }
        actions = ctx["actions"]
        actions["actions"][0]["url"] = reverse_lazy("inventory:batches:update", kwargs=url_kwargs)
        ctx["actions"] = actions

        return ctx

    def get_success_url(self):
        supply_reference = self.kwargs.get("supply_reference")
        kwargs = {
            "supply_reference": supply_reference,
            "external_id": self.kwargs.get(self.slug_url_kwarg),
        }
        return reverse("inventory:batches:detail", kwargs=kwargs)


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class BatchCreateView(CustomCreateView):
    model = DEFAULT_MODEL
    form_class = BatchBaseForm
    slug_field = "supply__external_id"
    slug_url_kwarg = "supply_reference"
    permission_required = "inventory.add_batch"
    template_name = "supplies/batches/create_or_update.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        supply_id = self.kwargs.get(self.slug_url_kwarg)
        supply = Supply.objects.get(external_id=supply_id)

        breadcrumbs = ctx.get("breadcrumb", [])
        breadcrumbs.insert(
            0, {"name": _("Supplies"), "url": reverse_lazy("inventory:supplies:list")}
        )

        breadcrumbs[1]["name"] = f"{supply.name} - {supply.code}"
        ctx["breadcrumbs"] = breadcrumbs
        return ctx

    def form_valid(self, form, **kwargs):
        service = BatchAppService()
        supply_reference = self.kwargs.get(self.slug_url_kwarg)

        try:
            supply_instance = Supply.objects.get(external_id=supply_reference)
            if not supply_instance:
                raise ValueError("Supply not found")

            # Prepare data for service layer
            batch_data = form.get_service_payload()
            batch_data["supply_id"] = supply_instance.id
            service.register_batch(payload=batch_data)

            # Show success message
            success_message = self.success_message.format(model=self.model._meta.verbose_name)
            messages.success(self.request, success_message, extra_tags="toast")

            # Redirect to the detail page
            return redirect(self.get_success_url())

        except ValidationError as e:
            self.handle_pydantic_error(e, form)
            return self.form_invalid(form)
        except Exception as e:
            return self.handle_error(str(e), e)

    def get_success_url(self):
        kwargs = {"external_id": self.kwargs.get(self.slug_url_kwarg)}
        return reverse("inventory:supplies:detail", kwargs=kwargs)


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class BatchUpdateView(CustomUpdateView):
    model = DEFAULT_MODEL
    form_class = BatchBaseForm
    permission_required = "inventory.change_batch"
    template_name = "supplies/batches/create_or_update.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        supply_id = self.kwargs.get("supply_reference")
        supply = Supply.objects.get(external_id=supply_id)

        breadcrumbs = ctx.get("breadcrumb", [])
        breadcrumbs.insert(
            0, {"name": _("Supplies"), "url": reverse_lazy("inventory:supplies:list")}
        )

        breadcrumbs[1]["name"] = f"{supply.name} - {supply.code}"
        ctx["breadcrumbs"] = breadcrumbs
        return ctx

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def form_valid(self, form):
        """Handle valid form submission with category and unit conversion."""
        service = BatchAppService()

        try:
            # Prepare data for service layer
            batch_data = form.get_service_payload()
            # Update supply instance
            instance = service.update_batch(instance=self.object, payload=batch_data)

            # Show success message
            reference = instance.number
            model_name = self.model._meta.verbose_name
            success_message = self.success_message.format(model=model_name, instance=reference)
            messages.success(self.request, success_message, extra_tags="toast")

            # Redirect to the detail page
            return redirect(instance.get_absolute_url())

        except ValidationError as e:
            self.handle_pydantic_error(e, form)
            return self.form_invalid(form)
        except Exception as e:
            return self.handle_error(str(e), e)

    def get_success_url(self):
        kwargs = {"external_id": self.kwargs.get("supply_reference")}
        return reverse("inventory:supplies:detail", kwargs=kwargs)
