from django.urls import path

from apps.catalogs.views.catalog_items import (
    CatalogItemCreateView,
    CatalogItemDetailView,
    CatalogItemListView,
    CatalogItemUpdateView,
)

app_name = "items"
SLUG = "<uuid:external_id>"

urlpatterns = [
    path("", CatalogItemListView.as_view(), name="list"),
    path(f"{SLUG}/", CatalogItemDetailView.as_view(), name="detail"),
    path("create/", CatalogItemCreateView.as_view(), name="create"),
    path(f"{SLUG}/update/", CatalogItemUpdateView.as_view(), name="update"),
]
