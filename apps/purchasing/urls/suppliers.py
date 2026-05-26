from django.urls import path

from apps.purchasing.views.suppliers import (
    SupplierDetailView,
    SupplierListView,
    SupplierCreateView,
    SupplierStatusUpdateView,
    SupplierUpdateView,
)

app_name = "suppliers"
SLUG = "<uuid:external_id>"

urlpatterns = [
    path("", SupplierListView.as_view(), name="list"),
    path(f"{SLUG}/", SupplierDetailView.as_view(), name="detail"),
    path("create/", SupplierCreateView.as_view(), name="create"),
    path(f"{SLUG}/update/", SupplierUpdateView.as_view(), name="update"),
    path(f"{SLUG}/update-status/", SupplierStatusUpdateView.as_view(), name="status"),
]
