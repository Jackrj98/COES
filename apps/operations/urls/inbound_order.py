from django.urls import path

from apps.operations.views.purchase_orders import (
    MarkOrderCancelView,
    MarkOrderCompletedView,
    PurchaseOrderCreateView,
    PurchaseOrderDetailView,
    PurchaseOrderListView,
    PurchaseOrderUpdateView,
)

app_name = "inbound_order"
SLUG = "<uuid:external_id>"

urlpatterns = [
    path("", PurchaseOrderListView.as_view(), name="list"),
    path(f"{SLUG}/", PurchaseOrderDetailView.as_view(), name="detail"),
    path("create/", PurchaseOrderCreateView.as_view(), name="create"),
    path(f"{SLUG}/update/", PurchaseOrderUpdateView.as_view(), name="update"),
    path(f"{SLUG}/mark-completed/", MarkOrderCompletedView.as_view(), name="completed"),
    path(f"{SLUG}/mark-cancelled/", MarkOrderCancelView.as_view(), name="cancelled"),
]
