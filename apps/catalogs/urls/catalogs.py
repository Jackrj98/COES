from django.urls import path

from apps.catalogs.views.catalogs import (
    CatalogCreateView,
    CatalogDetailView,
    CatalogListView,
    CatalogUpdateView,
)

app_name = "catalogs"
SLUG = "<uuid:external_id>"

urlpatterns = [
    path("", CatalogListView.as_view(), name="list"),
    path(f"{SLUG}/", CatalogDetailView.as_view(), name="detail"),
    path("create/", CatalogCreateView.as_view(), name="create"),
    path(f"{SLUG}/update/", CatalogUpdateView.as_view(), name="update"),
]
