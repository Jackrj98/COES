from django.urls import path

from apps.operations.views.exit_order import (
    ExitOrderCreateView,
    ExitOrderDetailView,
    ExitOrderListView,
)

app_name = "outbound_order"
SLUG = "<uuid:external_id>"

urlpatterns = [
    path("", ExitOrderListView.as_view(), name="list"),
    path(f"{SLUG}/", ExitOrderDetailView.as_view(), name="detail"),
    path("create/", ExitOrderCreateView.as_view(), name="create"),
    # path(f"{SLUG}/update/", SupplierUpdateView.as_view(), name="update"),
    # path(f"{SLUG}/update-status/", SupplierStatusUpdateView.as_view(), name="status"),
]
