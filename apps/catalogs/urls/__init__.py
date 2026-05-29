from django.urls import include, path

app_name = "catalogs"
SLUG = "<uuid:catalog_reference>"
urlpatterns = [
    path("catalogs/", include("apps.catalogs.urls.catalogs")),
    path("catalogs/<uuid:catalog_reference>/items/", include("apps.catalogs.urls.catalog_items")),
]
