from django.urls import path

from apps.inventory.views.movements import InventoryMovementListView

app_name = "movements"
SLUG = "<uuid:external_id>"

urlpatterns = [
    path("", InventoryMovementListView.as_view(), name="list"),
]
