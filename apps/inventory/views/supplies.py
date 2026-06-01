import logging
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count, F, Q, Sum
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
        batch_status = self.second_model.Status.ACTIVE
        return (
            super()
            .get_queryset()
            .select_related("category", "unit_of_measure")
            .annotate(
                total_stock=Sum(
                    "batches__stock",
                    filter=Q(batches__status=batch_status, batches__deleted_at__isnull=True),
                ),
                active_batches_count=Count(
                    "batches",
                    filter=Q(batches__status=batch_status, batches__deleted_at__isnull=True),
                ),
            )
        )

    def get_object(self, queryset=None):
        """Cache the object to avoid duplicate queries."""
        if not hasattr(self, "_cached_object"):
            self._cached_object = super().get_object(queryset)  # noqa
        return self._cached_object

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        supply = self.get_object()
        # Calculate stock percentage (capped at 100%)
        ctx["stock_percentage"] = self._calculate_stock_percentage(supply)
        # Additional context
        ctx["batch"] = self.second_model
        ctx["filter_form"] = BatchFilterForm

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
        data = form.cleaned_data
        service = SupplyAppService()
        uploaded_file = self.request.FILES.get("image_url")

        try:
            data.pop("image_url")
            category = data.pop("category")
            unit_of_measure = data.pop("unit_of_measure")
            data["category_id"] = category.id
            data["unit_of_measure_id"] = unit_of_measure.id

            service.register_supply(payload={**data}, file=uploaded_file)
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
        """Handle valid form submission with category and unit conversion."""
        cleaned_data = form.cleaned_data
        service = SupplyAppService()
        uploaded_file = self.request.FILES.get("image_url")

        try:
            # Prepare data for service layer
            supply_data = self._prepare_supply_data(cleaned_data)

            # Update supply instance
            instance = service.update_supply(
                instance=self.get_object(), payload=supply_data, file=uploaded_file
            )

            # Show success message
            self._show_success_message(instance)

            return redirect(self.get_success_url())

        except ValidationError as e:
            self.handle_pydantic_error(e, form)
            return self.form_invalid(form)
        except Exception as e:
            return self.handle_error(str(e), e)

    @staticmethod
    def _prepare_supply_data(cleaned_data):
        """Transform form data for the service layer.
        Converts category and unit_of_measure objects to their IDs.
        """
        data = cleaned_data.copy()  # Avoid mutating original

        # Remove file field (handled separately)
        data.pop("image_url", None)

        # Extract and convert foreign keys to IDs
        category = data.pop("category", None)
        unit_of_measure = data.pop("unit_of_measure", None)

        if category:
            data["category_id"] = category.id

        if unit_of_measure:
            data["unit_of_measure_id"] = unit_of_measure.id

        return data

    def _show_success_message(self, instance):
        """Display a success message after a successful update."""
        reference = instance.name[:10]
        model_name = self.model._meta.verbose_name

        messages.success(
            self.request,
            self.success_message.format(model=model_name, instance=reference),
            extra_tags="toast",
        )

    def form_invalid(self, form):
        messages.warning(self.request, self.failure_message)
        return self.render_to_response(self.get_context_data(form=form))
