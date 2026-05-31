from django.urls import path

from apps.inventory.views.supplies import SupplyListView, SupplyDetailView

app_name = "supplies"
SLUG = "<uuid:external_id>"

urlpatterns = [
    path("", SupplyListView.as_view(), name="list"),
    path(f"{SLUG}/", SupplyDetailView.as_view(), name="detail"),
    #  path("create/", CatalogCreateView.as_view(), name="create"),
    #  path(f"{SLUG}/update/", CatalogUpdateView.as_view(), name="update"),
]
