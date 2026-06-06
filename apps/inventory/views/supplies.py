import logging
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count, F, Q, Sum
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from pydantic import ValidationError

from apps.core.views.base import (
    CustomCreateView,
    CustomDetailView,
    CustomListView,
    CustomUpdateView,
)
from apps.inventory.forms import BatchFilterForm, SupplyBaseForm, SupplyFilterForm
from apps.inventory.layers.applications import SupplyAppService
from apps.inventory.models import Batch, Supply
from apps.security.layers.security import SecurityService

logger = logging.getLogger(__name__)

DEFAULT_MODEL = Supply
SECOND_MODEL = Batch
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
        ctx["actions"]["menu_actions"]["add"]["url"] = reverse_lazy("inventory:supplies:create")

        total_supplies, stock_normal, stock_critical, expiring_batches = self._metrics()
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

    def _metrics(self):
        supplies = self.object_list
        batch_status = Batch.BatchStatus
        thirty_days_from_now = timezone.now() + timedelta(days=30)

        total_supplies = supplies.filter(deleted_at__isnull=True).count()
        supplies_with_stock = Supply.objects.annotate(
            total_stock=Sum(
                "batches__current_quantity", filter=Q(batches__status=batch_status.ACTIVE)
            )
        )
        stock_normal = supplies_with_stock.filter(total_stock__gt=F("stock_min")).count()
        stock_critical = supplies_with_stock.filter(
            Q(total_stock__lte=F("stock_min")) | Q(total_stock__isnull=True)
        ).count()

        expiring_batches = Batch.objects.filter(
            status=batch_status.ACTIVE, expiry_date__lte=thirty_days_from_now
        ).count()

        return total_supplies, stock_normal, stock_critical, expiring_batches


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class SupplyDetailView(CustomDetailView):
    """View for displaying supply details with stock information."""

    app_name = "supplies"
    model = DEFAULT_MODEL
    second_model = SECOND_MODEL
    success_url = DEFAULT_LIST_URL
    template_name = "supplies/detail.html"
    permission_required = ["inventory.view_supply", "inventory.view_batch"]

    def get_queryset(self):
        """Optimize a query with select_related and annotated stock data."""
        batch_status = self.second_model.BatchStatus.ACTIVE
        return (
            super()
            .get_queryset()
            .select_related("category", "unit_of_measure")
            .annotate(
                total_stock=Sum(
                    "batches__current_quantity",
                    filter=Q(batches__status=batch_status, batches__deleted_at__isnull=True),
                ),
                active_batches_count=Count(
                    "batches",
                    filter=Q(batches__status=batch_status, batches__deleted_at__isnull=True),
                ),
            )
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        supply = self.object

        ctx["batch"] = self.second_model
        ctx["filter_form"] = BatchFilterForm
        ctx["ui_map"] = self.second_model.BatchStatus.get_ui_map()
        ctx["stock_percentage"] = self._calculate_stock_percentage(supply)
        url_kwargs = {"supply_reference": supply.external_id}
        ctx["batch_list_url"] = reverse_lazy("inventory:batches:list", kwargs=url_kwargs)

        self.add_custom_action(
            context=ctx,
            action={
                "icon": "bi bi-plus-lg",
                "order": 0,
                "name": "add batch",
                "title": _("Add batch"),
                "action": "add_batch",
                "description": "",
                "url": reverse_lazy("inventory:batches:create", kwargs=url_kwargs),
            },
        )
        return ctx

    def get_success_url(self):
        """Return the success URL after form submission."""
        return self.success_url

    @staticmethod
    def _calculate_stock_percentage(supply):
        """Calculate stock percentage based on total_stock and stock_min."""
        stock_val = getattr(supply, "total_stock", 0) or 0
        min_val = supply.stock_min

        if min_val > 0 and stock_val > 0:
            percentage = (stock_val / min_val) * 100
            return min(round(percentage), 100)
        return 0


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class SupplyCreateView(CustomCreateView):
    model = DEFAULT_MODEL
    form_class = SupplyBaseForm
    success_url: str = DEFAULT_LIST_URL
    permission_required = "inventory.add_supply"
    template_name = "supplies/create_or_update.html"

    def form_valid(self, form, **kwargs):
        service = SupplyAppService()

        try:
            # Prepare data for service layer
            supply_data = form.get_service_payload()
            uploaded_file = self.request.FILES.get("image_url")

            # Register supply
            service.register_supply(payload=supply_data, file=uploaded_file)

            # Show success message
            msg = self.success_message.format(model=self.model._meta.verbose_name)
            messages.success(self.request, msg, extra_tags="toast")
            return redirect(self.success_url)

        except ValidationError as e:
            self.handle_pydantic_error(e, form)
            return self.form_invalid(form)
        except Exception as e:
            return self.handle_error(str(e), e)


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class SupplyUpdateView(CustomUpdateView):
    model = DEFAULT_MODEL
    form_class = SupplyBaseForm
    success_url: str = DEFAULT_LIST_URL
    permission_required = "inventory.change_supply"
    template_name = "supplies/create_or_update.html"

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def get_object(self, queryset=None):
        if not hasattr(self, "_cached_object"):
            self._cached_object = super().get_object(queryset)  # noqa
        return self._cached_object

    def form_valid(self, form):
        """Handle valid form submission with category and unit conversion."""
        service = SupplyAppService()

        try:
            # Prepare data for service layer
            supply_data = form.get_service_payload()
            uploaded_file = self.request.FILES.get("image_url")

            # Update supply instance
            instance = service.update_supply(
                instance=self.get_object(), payload=supply_data, file=uploaded_file
            )

            # Show success message
            reference = instance.name[:10]
            msg = self.success_message.format(
                model=self.model._meta.verbose_name, instance=reference
            )
            messages.success(self.request, msg, extra_tags="toast")
            return redirect(self.get_success_url())

        except ValidationError as e:
            self.handle_pydantic_error(e, form)
            return self.form_invalid(form)
        except Exception as e:
            return self.handle_error(str(e), e)


@require_GET
@csrf_exempt
def search_supplies(request):
    search_term = request.GET.get("q", "").strip()
    movement_type = request.GET.get("type", "").strip()
    exclude_ids = [id for id in request.GET.get("exclude_ids", "").split(",") if id]

    supplies = SupplyAppService().retrieve_by_term(search_term, movement_type=movement_type)

    if exclude_ids:
        supplies = supplies.exclude(code__in=exclude_ids)

    supplies = supplies[:20]

    results = [
        {
            "id": supply.code,
            "text": f"{supply.name} - {supply.unit_of_measure.name} ({supply.unit_of_measure.extra})",
            "code": supply.code,
            "name": supply.name,
            "stock": supply.total_stock,
            "stock_min": supply.stock_min,
        }
        for supply in supplies
    ]

    return JsonResponse(
        {
            "results": results,
            "pagination": {"more": False},
        }
    )
