from django.urls import path

from apps.inventory.views.movements import (
    InventoryMovementCreateView,
    InventoryMovementDetailView,
    InventoryMovementListView,
    InventoryMovementOutboundCreateView,
    InventoryMovementUpdateView,
)

app_name = "movements"
SLUG = "<uuid:external_id>"

urlpatterns = [
    path("", InventoryMovementListView.as_view(), name="list"),
    path(f"{SLUG}/", InventoryMovementDetailView.as_view(), name="detail"),
    path("inbound/", InventoryMovementCreateView.as_view(), name="inbound"),
    path("outbound/", InventoryMovementOutboundCreateView.as_view(), name="outbound"),
    path("adjustment/", InventoryMovementCreateView.as_view(), name="adjustment"),
    path(f"{SLUG}/update/", InventoryMovementUpdateView.as_view(), name="update"),
]
