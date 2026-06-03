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
from apps.inventory.forms import (
    BatchFilterForm,
    InventoryMovementBaseForm,
    InventoryMovementFilterForm,
    MovementFormSet,
    SupplyBaseForm,
)
from apps.inventory.layers.applications import InventoryMovementAppService, SupplyAppService
from apps.inventory.models import Batch, InventoryMovement, Supply
from apps.security.layers.security import SecurityService

logger = logging.getLogger(__name__)

DEFAULT_MODEL = InventoryMovement
BASE_APPS_URL = "inventory:movements"
DEFAULT_LIST_URL = reverse_lazy(f"{BASE_APPS_URL}:list")


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class InventoryMovementListView(CustomListView):
    model = DEFAULT_MODEL
    form_class = InventoryMovementFilterForm
    success_url: str = DEFAULT_LIST_URL
    template_name = "inventory_movements/datatable.html"
    permission_required = "inventory.view_inventorymovement"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["object"] = self.model
        ctx["ui_map"] = self.model.Status.get_ui_map()
        ctx["type_ui_map"] = self.model.Type.get_ui_map()
        ctx["description"] = _("Management of registered inventory movements")
        return ctx

    def get_actions(self):
        return {
            "menu_actions": {
                "title": _("Actionable"),
                "actions": [
                    {
                        "title": _("Register inbound movement"),
                        "icon": "bi bi-plus-lg",
                        "url": reverse_lazy(f"{BASE_APPS_URL}:inbound"),
                    },
                    {
                        "title": _("Register outbound movement"),
                        "icon": "bi bi-dash-lg",
                        "url": reverse_lazy(f"{BASE_APPS_URL}:outbound"),
                    },
                    {
                        "title": _("Register stock adjustment"),
                        "icon": "bi bi-arrow-repeat",
                        "url": reverse_lazy(f"{BASE_APPS_URL}:adjustment"),
                    },
                ],
            }
        }

    def retrieve_data(self, params):
        return InventoryMovementAppService().retrieve_movements(params)

    def get_success_url(self):
        return self.success_url

    def _metrics(self):
        supplies = self.object_list
        thirty_days_from_now = timezone.now() + timedelta(days=30)

        total_supplies = supplies.filter(deleted_at__isnull=True).count()
        supplies_with_stock = Supply.objects.annotate(
            total_stock=Sum("batches__stock", filter=Q(batches__status=Batch.Status.ACTIVE))
        )
        stock_normal = supplies_with_stock.filter(total_stock__gt=F("stock_min")).count()
        stock_critical = supplies_with_stock.filter(
            Q(total_stock__lte=F("stock_min")) | Q(total_stock__isnull=True)
        ).count()

        expiring_batches = Batch.objects.filter(
            status=Batch.Status.ACTIVE, due_date__lte=thirty_days_from_now
        ).count()

        return total_supplies, stock_normal, stock_critical, expiring_batches


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class InventoryMovementDetailView(CustomDetailView):
    """View for displaying supply details with stock information."""

    app_name = "supplies"
    model = DEFAULT_MODEL
    success_url = DEFAULT_LIST_URL
    template_name = "inventory_movements/detail.html"
    permission_required = "inventory.view_inventorymovement"

    def get_queryset(self):
        """Optimize a query with select_related and annotated stock data."""
        return super().get_queryset().select_related("category", "unit_of_measure")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        supply = self.object

        ctx["batch"] = self.second_model
        ctx["filter_form"] = BatchFilterForm
        ctx["ui_map"] = self.second_model.Status.get_ui_map()
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
class InventoryMovementCreateView(CustomCreateView):
    model = DEFAULT_MODEL
    form_class = InventoryMovementBaseForm
    second_form_class = MovementFormSet
    success_url: str = DEFAULT_LIST_URL
    permission_required = "inventory.add_inventorymovement"
    template_name = "inventory_movements/create_or_update.html"

    def get_initial(self):
        initial = super().get_initial()
        initial["movement_type"] = self.model.Type.INBOUND
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["movement_types"] = self.model.Type.choices
        ctx["title"] = ctx["title"].capitalize()
        ctx["concept_list"] = [
            "Compra de insumos",
            "Ajuste por inventario inicial",
            "Devolución de proveedor",
        ]
        if self.request.method == "GET":
            ctx["movement_formset"] = self.second_form_class(
                queryset=InventoryMovement.objects.none(), prefix="movements"
            )
        else:
            ctx["movement_formset"] = self.second_form_class(
                self.request.POST or None, prefix="movements"
            )

        return ctx

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
class InventoryMovementOutboundCreateView(CustomCreateView):
    model = DEFAULT_MODEL
    form_class = InventoryMovementBaseForm
    second_form_class = MovementFormSet
    success_url: str = DEFAULT_LIST_URL
    permission_required = "inventory.add_inventorymovement"
    template_name = "inventory_movements/create_or_update.html"

    def get_initial(self):
        initial = super().get_initial()
        initial["movement_type"] = self.model.Type.OUTBOUND
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["movement_types"] = self.model.Type.choices
        ctx["title"] = ctx["title"].capitalize()
        ctx["concept_list"] = [
            "Compra de insumos",
            "Ajuste por inventario inicial",
            "Devolución de proveedor",
        ]
        if self.request.method == "GET":
            ctx["movement_formset"] = self.second_form_class(
                queryset=InventoryMovement.objects.none(), prefix="movements"
            )
        else:
            ctx["movement_formset"] = self.second_form_class(
                self.request.POST or None, prefix="movements"
            )

        return ctx


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class InventoryMovementUpdateView(CustomUpdateView):
    model = DEFAULT_MODEL
    form_class = SupplyBaseForm
    success_url: str = DEFAULT_LIST_URL
    permission_required = "inventory.change_inventorymovement"
    template_name = "inventory_movements/create_or_update.html"

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
