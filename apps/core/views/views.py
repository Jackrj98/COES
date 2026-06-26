import json
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count, F, Q, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from apps.inventory.models import Batch, InventoryMovement, Supply


class IndexView(LoginRequiredMixin, TemplateView):
    template_name = "layouts/base.html"
    extra_context = {"title": "Home"}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self._get_dashboard_metrics())
        return context

    def _get_dashboard_metrics(self):
        today = timezone.now().date()
        start_of_month = today.replace(day=1)
        expiry_threshold = today + timedelta(days=180)

        supplies = self._annotate_supply_stats(expiry_threshold)
        classification = self._classify_supplies(supplies, today)
        movements = self._get_monthly_movements(start_of_month)
        daily_movements = self._get_daily_movements(days=30)
        rankings = self._get_rankings()

        return {
            "inventory": self._build_inventory_cards(classification),
            "alerts": self._build_alerts(classification),
            "movements": movements,
            "daily_movements_json": json.dumps(daily_movements, cls=DjangoJSONEncoder),
            "rankings": rankings,
        }

    # ── Private helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _annotate_supply_stats(expiry_threshold):
        """Single query: stock, value and expiry flag computed entirely in SQL."""
        today = timezone.now().date()
        active_batch = Q(batches__status=Batch.StatusChoices.ACTIVE)

        return Supply.active.annotate(
            total_stock=Sum("batches__current_quantity", filter=active_batch),
            total_value=Sum(
                F("batches__current_quantity") * F("batches__unit_cost"),
                filter=active_batch,
            ),
            has_expiring_batch=Count(
                "batches",
                filter=active_batch
                & Q(batches__expiry_date__gte=today)
                & Q(batches__expiry_date__lte=expiry_threshold),
            ),
        ).prefetch_related("batches")

    @staticmethod
    def _classify_supplies(supplies, today):
        """Single pass over the annotated queryset. No re-querying batches,
        no recomputation — every numeric value used here already came from SQL.

        Also collects the *detail* rows needed for the alert panels
        (critical/warning), so the template doesn't need a second loop.
        """
        critical_count = 0
        low_count = 0
        expiring_count = 0
        total_value = 0

        critical_alerts = []
        warning_alerts = []

        for supply in supplies:
            stock = supply.total_stock or 0
            value = supply.total_value or 0
            is_critical = stock <= supply.stock_min
            is_low = stock <= supply.stock_min * 1.5

            if is_critical:
                critical_count += 1
                critical_alerts.append(
                    {
                        "title": supply.name,
                        "description": _("Stock: %(stock)s / min %(min)s — Critical")
                        % {"stock": stock, "min": supply.stock_min},
                        "url": supply.get_absolute_url(),
                    }
                )
            elif is_low:
                low_count += 1
                warning_alerts.append(
                    {
                        "title": supply.name,
                        "description": _("Stock approaching minimum"),
                        "url": supply.get_absolute_url(),
                    }
                )

            if supply.has_expiring_batch:
                expiring_count += 1
                IndexView._add_expiring_batch_alerts(supply, today, warning_alerts, critical_alerts)

            total_value += value

        return {
            "total_supplies": len(supplies),
            "critical_count": critical_count,
            "low_count": low_count,
            "expiring_count": expiring_count,
            "total_value": total_value,
            "critical_alerts": critical_alerts,
            "warning_alerts": warning_alerts,
        }

    @staticmethod
    def _add_expiring_batch_alerts(supply, today, warning_alerts, critical_alerts):
        """Adds one alert per expiring/expired batch of this supply.
        Already-expired batches go to critical; soon-to-expire go to warning.
        """
        for batch in supply.batches.all():
            if batch.status != Batch.StatusChoices.ACTIVE:
                continue

            if batch.is_expired:
                critical_alerts.append(
                    {
                        "title": batch.batch_number,
                        "description": _("Expired %(days)s days ago — %(supply)s")
                        % {"days": (today - batch.expiry_date).days, "supply": supply.name},
                        "url": supply.get_absolute_url(),
                    }
                )
            elif batch.days_until_expiry is not None and batch.days_until_expiry <= 30:
                warning_alerts.append(
                    {
                        "title": batch.batch_number,
                        "description": _("Expires in %(days)s days — %(supply)s")
                        % {"days": batch.days_until_expiry, "supply": supply.name},
                        "url": supply.get_absolute_url(),
                    }
                )

    @staticmethod
    def _build_alerts(classification):
        """Shapes the alert lists exactly as the dashboard template expects them."""
        return {
            "critical": classification["critical_alerts"],
            "warning": classification["warning_alerts"],
        }

    @staticmethod
    def _get_monthly_movements(start_of_month):
        aggregates = InventoryMovement.objects.filter(created_at__gte=start_of_month).aggregate(
            total=Count("id"),
            inbound=Count("id", filter=Q(movement_type=InventoryMovement.Type.INBOUND)),
            outbound=Count("id", filter=Q(movement_type=InventoryMovement.Type.OUTBOUND)),
            adjustments=Count("id", filter=Q(movement_type=InventoryMovement.Type.ADJUSTMENT)),
            quantity_moved=Sum("quantity"),
        )
        aggregates["quantity_moved"] = aggregates["quantity_moved"] or 0
        return aggregates

    @staticmethod
    def _get_daily_movements(days=30):
        """Returns movements grouped by day for the last N days, split by type.
        Shaped for an ApexCharts stacked bar chart (categories + series).
        """
        today = timezone.now().date()
        start_date = today - timedelta(days=days - 1)

        raw = (
            InventoryMovement.objects.filter(created_at__date__gte=start_date)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(
                inbound=Count("id", filter=Q(movement_type=InventoryMovement.Type.INBOUND)),
                outbound=Count("id", filter=Q(movement_type=InventoryMovement.Type.OUTBOUND)),
                adjustments=Count("id", filter=Q(movement_type=InventoryMovement.Type.ADJUSTMENT)),
            )
            .order_by("day")
        )

        # Index by date for O(1) lookup — fills gaps with zero so the chart
        # always shows all 30 days, even days with no movements.
        by_day = {row["day"]: row for row in raw}

        categories = []
        inbound_series = []
        outbound_series = []
        adjustments_series = []

        for offset in range(days):
            day = start_date + timedelta(days=offset)
            row = by_day.get(day, {"inbound": 0, "outbound": 0, "adjustments": 0})

            categories.append(day.strftime("%d %b"))
            inbound_series.append(row["inbound"])
            outbound_series.append(row["outbound"])
            adjustments_series.append(row["adjustments"])

        return {
            "categories": categories,
            "series": [
                {"name": _("Inbounds"), "data": inbound_series},
                {"name": _("Outbounds"), "data": outbound_series},
                {"name": _("Adjustments"), "data": adjustments_series},
            ],
        }

    @staticmethod
    def _get_rankings():
        outbound_filter = Q(batches__movements__movement_type=InventoryMovement.Type.OUTBOUND)

        top_outbound = Supply.active.annotate(
            outbound_quantity=Sum("batches__movements__quantity", filter=outbound_filter)
        ).order_by("-outbound_quantity")[:10]

        top_value = Supply.active.annotate(
            total_val=Sum(F("batches__current_quantity") * F("batches__unit_cost"))
        ).order_by("-total_val")[:8]

        return {
            "top_outbound": top_outbound,
            "top_value": top_value,
        }

    @staticmethod
    def _build_inventory_cards(classification):
        return [
            {
                "label": _("Supplies available"),
                "value": classification["total_supplies"],
                "icon": "bi-box-seam",
                "color": "primary",
                "small": _("Total in stock"),
            },
            {
                "label": _("Critical stock"),
                "value": classification["critical_count"],
                "icon": "bi-exclamation-triangle",
                "color": "danger",
                "small": _("Attention required"),
            },
            {
                "label": _("Low stock"),
                "value": classification["low_count"],
                "icon": "bi-exclamation-circle",
                "color": "secondary",
                "small": _("Valued inventory"),
            },
            {
                "label": _("Expiring soon"),
                "value": classification["expiring_count"],
                "icon": "bi-calendar-minus",
                "color": "warning",
                "small": _("Next 6 months"),
            },
        ]


class CustomPermissionDeniedView(TemplateView):
    template_name = "errors/403.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["exception"] = self.kwargs.get("exception")
        return context

    def get(self, request, *args, **kwargs):
        messages.error(request, _("You do not have permission to perform this action."))
        return self.render_to_response(self.get_context_data(**kwargs), status=403)


class CustomPageNotFoundView(TemplateView):
    template_name = "errors/404.html"

    def get(self, request, *args, **kwargs):
        return self.render_to_response(self.get_context_data(**kwargs), status=404)


class CustomServerErrorView(TemplateView):
    template_name = "errors/500.html"

    def get(self, request, *args, **kwargs):
        return self.render_to_response(self.get_context_data(**kwargs), status=500)


def handler403(request, exception=None):
    return CustomPermissionDeniedView.as_view()(request, exception=exception)


def handler404(request, exception=None):
    return CustomPageNotFoundView.as_view()(request, exception=exception)


def handler500(request):
    return CustomServerErrorView.as_view()(request)
