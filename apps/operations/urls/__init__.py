from django.urls import include, path

app_name = "operations"
urlpatterns = [
    path("suppliers/", include("apps.operations.urls.suppliers")),
]
