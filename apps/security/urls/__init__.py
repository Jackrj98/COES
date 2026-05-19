from django.urls import include, path

app_name = "security"
urlpatterns = [
    path("accounts/", include("apps.security.urls.authentication")),
    path("accounts/", include("apps.security.urls.users")),
]
