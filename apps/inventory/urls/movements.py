from django.urls import path

from apps.inventory.views.movements import (
    InventoryMovementCreateView,
    InventoryMovementDetailView,
    InventoryMovementListView,
    InventoryMovementUpdateView,
)

app_name = "movements"
SLUG = "<uuid:external_id>"

urlpatterns = [
    path("", InventoryMovementListView.as_view(), name="list"),
    path(f"{SLUG}/", InventoryMovementDetailView.as_view(), name="detail"),
    path("create/", InventoryMovementCreateView.as_view(), name="create"),
    path(f"{SLUG}/update/", InventoryMovementUpdateView.as_view(), name="update"),
]
