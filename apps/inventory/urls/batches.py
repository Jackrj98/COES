from django.urls import path

from apps.inventory.views.batches import (
    BatchCreateView,
    BatchDetailView,
    BatchListView,
    BatchUpdateView,
)

app_name = "batches"
SLUG = "<uuid:external_id>"

urlpatterns = [
    path("", BatchListView.as_view(), name="list"),
    path(f"{SLUG}/", BatchDetailView.as_view(), name="detail"),
    path("create/", BatchCreateView.as_view(), name="create"),
    path(f"{SLUG}/update/", BatchUpdateView.as_view(), name="update"),
]
