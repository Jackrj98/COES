from django.urls import include, path

app_name = "inventory"
SLUG = "<uuid:supply_reference>"
urlpatterns = [
    path("supplies", include("apps.inventory.urls.supplies")),
    # path("catalogs/<uuid:catalog_reference>/items/", include("apps.catalogs.urls.catalog_items")),
]
