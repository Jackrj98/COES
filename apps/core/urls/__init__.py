from django.urls import include, path

app_name = "core"

urlpatterns = [
    path("", include("apps.core.urls.default")),
]
