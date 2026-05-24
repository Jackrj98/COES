from apps.core.layers.dto import DatatableSearchBase
from apps.security.models import User


class DatatableSearch(DatatableSearchBase):
    @classmethod
    def retrieve_users(cls, params):
        qs = cls._build_base_query(params, User, "status")
        qs = qs.select_related("person").prefetch_related("groups")
        group = params.request.GET.get("group")
        search = params.request.GET.get("search")

        if group:
            qs = qs.filter(groups__name=group)

        if search:
            search_fields = [
                "username",
                "email",
                "status",
                "person__last_name",
                "person__document_number",
                "groups__name",
            ]
            qs = cls._apply_search(qs, search, search_fields)

        return cls._prepare_response(params, qs)
