import logging
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db.models import F, Q, Sum
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from pydantic import ValidationError

from apps.core.views.base import (
    CustomCreateView,
    CustomDetailView,
    CustomListView,
    CustomUpdateView,
)
from apps.inventory.forms import SupplyFilterForm
from apps.inventory.layers.applications import SupplyAppService
from apps.inventory.models import Batch, Supply
from apps.security.layers.security import SecurityService

logger = logging.getLogger(__name__)

DEFAULT_MODEL = Supply
DEFAULT_LIST_URL = reverse_lazy("inventory:supplies:list")


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class SupplyListView(CustomListView):
    model = DEFAULT_MODEL
    form_class = SupplyFilterForm
    success_url: str = DEFAULT_LIST_URL
    template_name = "supplies/datatable.html"
    permission_required = "inventory.view_supply"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["object"] = self.model
        ctx["description"] = _("Management of registered supplies")
        ctx["actions"]["menu_actions"]["add"]["url"] = reverse_lazy("catalogs:catalogs:create")

        thirty_days_from_now = timezone.now() + timedelta(days=30)
        supplies = self.object_list

        total_supplies = supplies.filter(deleted_at__isnull=True).count()
        supplies_with_stock = Supply.objects.annotate(
            total_stock=Sum("batches__stock", filter=Q(batches__status=Batch.Status.ACTIVE))
        )
        stock_normal = supplies_with_stock.filter(total_stock__gt=F("stock_min")).count()
        stock_critical = supplies_with_stock.filter(
            Q(total_stock__lte=F("stock_min")) | Q(total_stock__isnull=True)
        ).count()

        expiring_batches = Batch.objects.filter(
            status=Batch.Status.ACTIVE, expiration_date__lte=thirty_days_from_now
        ).count()
        print(
            Batch.objects.filter(
                status=Batch.Status.ACTIVE, expiration_date__lte=thirty_days_from_now
            ).count()
        )
        ctx["metrics_list"] = [
            {
                "title": _("Total Supplies"),
                "value": total_supplies,
                "sub": _("registered"),
                "icon": "bi-boxes",
                "color": "primary",
            },
            {
                "title": _("Stock OK"),
                "value": stock_normal,
                "sub": _("above minimum"),
                "icon": "bi-check-lg",
                "color": "success",
            },
            {
                "title": _("Stock Critical"),
                "value": stock_critical,
                "sub": _("below minimum"),
                "icon": "bi bi-exclamation-circle",
                "color": "danger",
            },
            {
                "title": _("Expiring Batches"),
                "value": expiring_batches,
                "sub": _("next 30 days"),
                "icon": "bi-calendar-event-fill",
                "color": "warning",
            },
        ]
        return ctx

    def retrieve_data(self, params):
        return SupplyAppService().retrieve_suppliers(params)

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
        ctx["filter_form"] = "CatalogFilterForm"
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
        print(actions)

        return ctx

    def get_success_url(self):
        return self.success_url


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class CatalogCreateView(CustomCreateView):
    model = DEFAULT_MODEL
    form_class = "CatalogBaseForm"
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
        service = SupplyAppService()

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
    form_class = "CatalogBaseForm"
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
        service = SupplyAppService()
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
