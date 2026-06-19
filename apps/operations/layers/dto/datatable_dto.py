from apps.core.layers.dto import DatatableSearchBase
from apps.operations.models import (
    InboundOrder,
    OutboundOrder,
    Supplier,
)


class DatatableSearch(DatatableSearchBase):
    @classmethod
    def retrieve_suppliers(cls, params):
        search = params.request.GET.get("search")
        delivery_val = params.request.GET.get("delivery_days")

        qs = cls._build_base_query(params, Supplier, "is_active")

        if delivery_val:
            if delivery_val == "fast":
                qs = qs.filter(delivery_days__lte=5)
            elif delivery_val == "medium":
                # Rango entre 6 y 14 (ambos inclusive)
                qs = qs.filter(delivery_days__gte=6, delivery_days__lte=14)
            elif delivery_val == "slow":
                qs = qs.filter(delivery_days__gt=14)

        if search:
            search = search.strip()
            search_fields = [
                "business_name",
                "last_name",
                "email",
                "document_number",
            ]
            qs = cls._apply_search(qs, search, search_fields)

        return cls._prepare_response(params, qs)

    @classmethod
    def retrieve_orders(cls, params):
        search = params.request.GET.get("search")

        qs = cls._build_base_query(params, InboundOrder, "status")
        qs = qs.prefetch_related("details", "details__supply", "details__batch")

        if search:
            search = search.strip()
            search_fields = [
                "order_number",
                "supplier__last_name",
                "supplier__document_number",
                "created_by",
            ]
            qs = cls._apply_search(qs, search, search_fields)

        return cls._prepare_response(params, qs)

    @classmethod
    def retrieve_outbound_orders(cls, params):
        search = params.request.GET.get("search")

        qs = cls._build_base_query(params, OutboundOrder, "status")
        qs = qs.prefetch_related("details", "details__supply", "details__batch")

        if search:
            search = search.strip()
            search_fields = [
                "order_number",
                "created_by",
            ]
            qs = cls._apply_search(qs, search, search_fields)

        return cls._prepare_response(params, qs)
