from django.urls import path

from apps.inventory.views.supplies import (
    SupplyCreateView,
    SupplyDetailView,
    SupplyListView,
    SupplyUpdateView,
    get_supply_stock,
    search_supplies,
)

app_name = "supplies"
SLUG = "<uuid:external_id>"

urlpatterns = [
    path("", SupplyListView.as_view(), name="list"),
    path(f"{SLUG}/", SupplyDetailView.as_view(), name="detail"),
    path("create/", SupplyCreateView.as_view(), name="create"),
    path(f"{SLUG}/update/", SupplyUpdateView.as_view(), name="update"),
    path("stock/", get_supply_stock, name="stock"),
    path("search/", search_supplies, name="search"),
]
