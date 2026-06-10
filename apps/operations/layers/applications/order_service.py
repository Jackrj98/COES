import logging

from django.db.models import Count

from apps.operations.layers.builders import ExitOrderBuilder
from apps.operations.layers.dto import DatatableSearch

logger = logging.getLogger(__name__)


class OrderAppService:
    @staticmethod
    def retrieve_exit_orders(params):
        fields = [
            "external_id",
            "order_number",
            "motive",
            "requested_by",
            "subtotal",
            "total",
            "status",
            "created_at",
            "updated_at",
        ]
        try:
            DatatableSearch.retrieve_exit_orders(params)
            queryset = params.items.annotate(items=Count("details"))
            qs = list(queryset.values(*fields, "items"))
            return params.result(qs)
        except Exception as e:
            logger.exception(f"Failed to fetch exit orders: {e}")
            return []

    @staticmethod
    def create_exit_order(payload):
        return (
            ExitOrderBuilder()
            .set_status(payload.status)
            .requested_by(payload.requested_by)
            .set_observations(payload.observations)
            .set_motive(payload.motive)
            .save()
            .build()
        )
