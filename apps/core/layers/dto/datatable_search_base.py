from datetime import datetime

from django.db.models import Q
from django.utils.timezone import make_aware


class DatatableSearchBase:
    @staticmethod
    def _build_base_query(params, model, status_field="status"):
        """Build a base query with common filters (status, date range)."""
        queryset = Q()
        request = params.request.GET
        status = request.get(status_field)
        created_at = request.get("created_at")
        created_at_from = request.get("created_at_from")
        created_at_to = request.get("created_at_to")

        if status:
            queryset &= Q(**{status_field: status})

        if created_at:
            dt = make_aware(datetime.strptime(created_at, "%Y-%m-%d"))
            dt_end = dt.replace(hour=23, minute=59, second=59)
            queryset &= Q(created_at__gte=dt, created_at__lte=dt_end)

        if created_at_from:
            dt_from = make_aware(datetime.strptime(created_at_from, "%Y-%m-%d"))
            queryset &= Q(created_at__gte=dt_from)

        if created_at_to:
            dt_to = make_aware(datetime.strptime(created_at_to, "%Y-%m-%d"))
            dt_end = dt_to.replace(hour=23, minute=59, second=59)
            queryset &= Q(created_at__lte=dt_end)

        return model.objects.filter(queryset, deleted_at__isnull=True)

    @staticmethod
    def _apply_search(queryset, search, search_fields):
        """Apply a search filter if the search term exists."""
        if not search:
            return queryset

        search_query = Q()
        for field in search_fields:
            search_query |= Q(**{f"{field}__icontains": search})
        return queryset.filter(search_query)

    @staticmethod
    def _prepare_response(params, queryset):
        """Prepare the final response with counts and items."""
        params.total = queryset.count()
        params.count = queryset.count()
        params.items = params.init_items(queryset)
        return params
