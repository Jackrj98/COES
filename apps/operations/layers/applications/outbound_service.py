import logging

from django.db.models import Count, Sum

from apps.operations.layers.dto import DatatableSearch

logger = logging.getLogger(__name__)


class OutboundOrderService:
    REQUIRED_ORDER_FIELDS = ["motive"]

    @staticmethod
    def get_outbound_orders(params):
        fields = [
            "external_id",
            "order_number",
            "supplier__business_name",
            "supplier__first_name",
            "supplier__last_name",
            "supplier__document_number",
            "scheduled_date",
            "received_date",
            "status",
            "created_at",
            "created_by",
            "updated_at",
            "updated_by",
        ]
        try:
            DatatableSearch.retrieve_outbound_orders(params)
            queryset = params.items.annotate(
                line_items=Count("details"), total=Sum("details__unit_cost")
            )
            qs = list(queryset.values(*fields, "line_items", "total"))
            return params.result(qs)
        except Exception as e:
            logger.exception(f"Failed to fetch outbound orders: {e}")
            return []
