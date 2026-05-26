from django.urls import include, path

app_name = "purchasing"
urlpatterns = [
    path("suppliers/", include("apps.purchasing.urls.suppliers")),
]
