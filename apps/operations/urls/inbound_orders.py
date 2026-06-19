from django.urls import path

from apps.operations.views.inbound_orders import (
    InboundOrderCreateView,
    InboundOrderMarkCancelView,
    InboundOrderMarkCompletedView,
    InboundOrdersDetailView,
    InboundOrdersListView,
    InboundOrderUpdateView,
)

app_name = "inbound"
SLUG = "<uuid:external_id>"

urlpatterns = [
    path("", InboundOrdersListView.as_view(), name="list"),
    path(f"{SLUG}/", InboundOrdersDetailView.as_view(), name="detail"),
    path("create/", InboundOrderCreateView.as_view(), name="create"),
    path(f"{SLUG}/update/", InboundOrderUpdateView.as_view(), name="update"),
    path(f"{SLUG}/mark-completed/", InboundOrderMarkCompletedView.as_view(), name="completed"),
    path(f"{SLUG}/mark-cancelled/", InboundOrderMarkCancelView.as_view(), name="cancelled"),
]
