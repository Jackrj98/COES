from django.urls import include, path

app_name = "inventory"
SLUG = "<uuid:supply_reference>"
urlpatterns = [
    path("supplies/", include("apps.inventory.urls.supplies")),
    path(f"supplies/{SLUG}/batches/", include("apps.inventory.urls.batches")),
]
