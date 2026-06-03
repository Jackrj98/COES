from datetime import date, timedelta

from django.db.models import F, Sum

from apps.core.layers.dto import DatatableSearchBase
from apps.inventory.models import Batch, InventoryMovement, Supply


class DatatableSearch(DatatableSearchBase):
    @classmethod
    def retrieve_supplies(cls, params):
        stock_filter = params.request.GET.get("stock")
        category_filter = params.request.GET.get("category")

        qs = cls._build_base_query(params, Supply, "is_active")
        qs = qs.annotate(total_stock=Sum("batches__stock"))

        if stock_filter:
            if stock_filter == "critical":
                qs = qs.filter(total_stock__lte=F("stock_min") * 0.2)
            elif stock_filter == "low":
                qs = qs.filter(
                    total_stock__gt=F("stock_min") * 0.2, total_stock__lte=F("stock_min")
                )
            elif stock_filter == "normal":
                qs = qs.filter(total_stock__gt=F("stock_min"))

        if category_filter:
            qs = qs.filter(category__code=category_filter)

        search = params.request.GET.get("search")

        if search:
            search = search.strip()
            search_fields = ["name", "code"]
            qs = cls._apply_search(qs, search, search_fields)

        return cls._prepare_response(params, qs)

    @classmethod
    def retrieve_batches(cls, params):
        expiration_filter = params.request.GET.get("expiration")

        qs = cls._build_base_query(params, Batch, "status")

        if expiration_filter:
            today = date.today()
            in_30_days = today + timedelta(days=30)
            if expiration_filter == "current":
                qs = qs.filter(due_date=in_30_days)
            elif expiration_filter == "expiring":
                qs = qs.filter(due_date=today, due_date__lte=in_30_days)
            elif expiration_filter == "expired":
                qs = qs.filter(due_date__lte=today)

        search = params.request.GET.get("search")

        if search:
            search = search.strip()
            search_fields = ["number"]
            qs = cls._apply_search(qs, search, search_fields)

        return cls._prepare_response(params, qs)

    @classmethod
    def retrieve_inventory_movements(cls, params):
        search = params.request.GET.get("search")
        movement_type = params.request.GET.get("movement_type")

        # Generate the base query
        qs = cls._build_base_query(params, InventoryMovement, "status")
        qs = qs.select_related("batch__supply")

        if movement_type:
            qs = qs.filter(movement_type=movement_type)

        if search:
            search = search.strip()
            search_fields = [
                "concept",
                "batch__number",
                "batch__supplier__name",
                "batch__supplier__code",
            ]
            qs = cls._apply_search(qs, search, search_fields)

        return cls._prepare_response(params, qs)
