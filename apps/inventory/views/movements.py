import logging
from datetime import timedelta

from django.contrib.auth.decorators import user_passes_test
from django.db.models import F, Q, Sum
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from apps.core.views.base import (
    CustomListView,
)
from apps.inventory.forms import (
    InventoryMovementFilterForm,
)
from apps.inventory.layers.applications import InventoryMovementAppService
from apps.inventory.layers.applications.report_service import (
    CSVExportService,
    ExcelExportService,
    InventoryReportService,
    MovementFilterService,
)
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
    template_name = "movements/datatable2.html"
    permission_required = "inventory.view_inventorymovements"
    filter_service = MovementFilterService()
    report_service = InventoryReportService()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["object"] = self.model
        ctx["ui_map"] = self.model.MovementStatusChoices.get_ui_map()
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

    def export_excel(self, request):
        filters = self.filter_service.extract_filters(request)
        report_data = self.report_service.generate_movement_report(filters)
        exporter = ExcelExportService(report_data, "inventory_movements")
        return exporter.generate()

    def export_csv(self, request):
        filters = self.filter_service.extract_filters(request)
        report_data = self.report_service.generate_movement_report(filters)
        exporter = CSVExportService(report_data, "inventory_movements")
        return exporter.generate()

    def post(self, request, *args, **kwargs):
        if "export_excel" in request.POST:
            return self.export_excel(request)
        elif "export_csv" in request.POST:
            return self.export_csv(request)
        return self.get(request, *args, **kwargs)

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
            status=Batch.BatchStatus.ACTIVE, expiry_date__lte=thirty_days_from_now
        ).count()

        return total_supplies, stock_normal, stock_critical, expiring_batches
