from django.urls import path

from apps.operations.views.outbound_orders import (
    OutboundOrderCreateView,
    OutboundOrderDetailView,
    OutboundOrderListView,
)

app_name = "outbound"
SLUG = "<uuid:external_id>"

urlpatterns = [
    path("", OutboundOrderListView.as_view(), name="list"),
    path(f"{SLUG}/", OutboundOrderDetailView.as_view(), name="detail"),
    path("create/", OutboundOrderCreateView.as_view(), name="create"),
]
