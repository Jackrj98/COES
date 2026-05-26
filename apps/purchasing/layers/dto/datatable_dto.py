from apps.core.layers.dto import DatatableSearchBase
from apps.purchasing.models import Supplier


class DatatableSearch(DatatableSearchBase):
    @classmethod
    def retrieve_suppliers(cls, params):
        reason = params.request.GET.get("reason")
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

        if reason:
            qs = qs.filter(reason=reason)

        search = params.request.GET.get("search")

        if search:
            search_fields = [
                "business_name",
                "email",
                "tax_id",
            ]
            qs = cls._apply_search(qs, search, search_fields)

        return cls._prepare_response(params, qs)
