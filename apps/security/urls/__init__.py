from django.urls import include, path

app_name = "security"
urlpatterns = [
    path("accounts/", include("apps.security.urls.auth")),
    path("accounts/", include("apps.security.urls.users")),
]
