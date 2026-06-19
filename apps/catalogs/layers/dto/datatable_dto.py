from apps.catalogs.models import Catalog, CatalogItem
from apps.core.layers.dto import DatatableSearchBase


class CatalogDatatableSearch(DatatableSearchBase):
    @classmethod
    def retrieve_catalogs(cls, params):
        parent_id = params.request.GET.get("parent_id")

        qs = cls._build_base_query(params, Catalog, "is_active")

        if parent_id:
            qs = qs.filter(parent_id=parent_id)

        search_query = params.request.GET.get("search")
        if search_query:
            search_fields = [
                "name",
                "code",
            ]
            qs = cls._apply_search(qs, search_query, search_fields)

        return cls._prepare_response(params, qs)

    @classmethod
    def retrieve_catalog_items(cls, params, catalog_reference):

        qs = cls._build_base_query(params, CatalogItem, "is_active")
        qs = qs.select_related("catalog").filter(catalog__external_id=catalog_reference)

        search_query = params.request.GET.get("search")
        if search_query:
            search_fields = [
                "name",
                "code",
            ]
            qs = cls._apply_search(qs, search_query, search_fields)

        return cls._prepare_response(params, qs)
